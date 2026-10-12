// Positive-half adapters of the author's BenchmarkMetaFBS8 configuration.
// No author library or cryptographic noise parameter is changed.
package main

import (
	"crypto/sha256"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"github.com/sp301415/tfhe-go/tfhe"
	"math"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"
)

func emit(kind string, value any) {
	b, e := json.Marshal(value)
	if e != nil {
		panic(e)
	}
	fmt.Printf("%s %s\n", kind, b)
}
func integer(s string) int {
	v, e := strconv.Atoi(s)
	if e != nil {
		panic(e)
	}
	return v
}
func require(ok bool, message string) {
	if !ok {
		panic(message)
	}
}
func arity(task string) int {
	switch task {
	case "mode3_4", "iqr3_4":
		return 4
	case "lower_median3_3", "max3_3", "range3_3", "mad3_3", "distinct3_3":
		return 3
	default:
		panic("task outside frozen seven instances")
	}
}
func target(task string, xs []int) int {
	n := arity(task)
	require(len(xs) == n, "ternary arity")
	for _, x := range xs {
		require(x >= 0 && x < 3, "ternary range")
	}
	s := append([]int(nil), xs...)
	sort.Ints(s)
	switch task {
	case "lower_median3_3":
		return s[(n-1)/2]
	case "mode3_4":
		counts := [3]int{}
		for _, x := range xs {
			counts[x]++
		}
		best := 0
		for x := 1; x < 3; x++ {
			if counts[x] > counts[best] {
				best = x
			}
		}
		return best
	case "max3_3":
		return s[n-1]
	case "range3_3":
		return s[n-1] - s[0]
	case "iqr3_4":
		return s[3*(n-1)/4] - s[(n-1)/4]
	case "mad3_3":
		d := make([]int, n)
		for i, x := range xs {
			d[i] = x - s[(n-1)/2]
			if d[i] < 0 {
				d[i] = -d[i]
			}
		}
		sort.Ints(d)
		return d[(n-1)/2]
	case "distinct3_3":
		counts := [3]bool{}
		for _, x := range xs {
			counts[x] = true
		}
		total := 0
		for _, seen := range counts {
			if seen {
				total++
			}
		}
		return total
	default:
		panic("unreachable task")
	}
}
func decodedTarget(task string, index int) int {
	n := arity(task)
	size := 1
	for i := 0; i < n; i++ {
		size *= 3
	}
	if index >= size {
		return 0
	}
	xs := make([]int, n)
	for i := range xs {
		xs[i] = index % 3
		index /= 3
	}
	return target(task, xs)
}

type Trial struct {
	phase    string
	index    int
	values   []int
	expected int
	kind     string
}

func readTrials(task, path string) []Trial {
	f, e := os.Open(path)
	if e != nil {
		panic(e)
	}
	rows, e := csv.NewReader(f).ReadAll()
	f.Close()
	if e != nil {
		panic(e)
	}
	require(len(rows) == 36, "exactly five warmups and thirty measured rows required")
	expectedHeader := "phase,index,task_id,inputs,expected,kind"
	require(strings.Join(rows[0], ",") == expectedHeader, "manifest header mismatch")
	out := make([]Trial, 0, 35)
	seen := map[string]bool{}
	for i, row := range rows[1:] {
		require(len(row) == 6, "manifest column count")
		phase := row[0]
		if i < 5 {
			require(phase == "warmup", "warmup ordering")
		} else {
			require(phase == "measured", "measured ordering")
		}
		key := phase + ":" + row[1]
		require(!seen[key], "duplicate phase/index")
		seen[key] = true
		var values []int
		var expected int
		require(row[2] == task, "task mismatch")
		for _, x := range strings.Split(row[3], ";") {
			values = append(values, integer(x))
		}
		expected = integer(row[4])
		require(target(task, values) == expected, "clear expected mismatch")
		out = append(out, Trial{phase, integer(row[1]), values, expected, row[5]})
	}
	return out
}
func main() {
	require(len(os.Args) == 3, "usage: dccsmall task_id input.csv")
	task, path := os.Args[1], os.Args[2]
	trials := readTrials(task, path)
	precision := 8
	half := 1 << (precision - 1)
	table := make([]byte, half)
	for x := range table {
		table[x] = byte(decodedTarget(task, x))
	}
	digest := sha256.Sum256(table)
	weights := make([]int, arity(task))
	weight := 1
	for i := range weights {
		weights[i] = weight
		weight *= 3
	}
	varianceFactor := 0
	for _, a := range weights {
		varianceFactor += a * a
	}
	// Verbatim public parameter-selection recipe from BenchmarkMetaFBS at precision 8.
	paramsLit := tfhe.ParamsMetaTemplate
	paramsLit.MessageModulus <<= (precision - 8)
	config := tfhe.DefaultSweepConfig()
	config.CapacityBits = tfhe.MetaFBSCapacityBits[precision]
	config.CapacityBitsMeta = tfhe.MetaFBSCapacityBitsMeta[precision]
	setupStart := time.Now()
	params, e := tfhe.SweepParameter(paramsLit, config)
	if e != nil {
		panic(e)
	}
	require(params.FullTorus() && !params.FullDomain(), "positive-half negacyclic parameter contract")
	fmt.Printf("AUTHOR_COMPILED_PARAMS %+v\n", params)
	tfhe.PrintParamsNoiseLevel(params, config)
	// Conservative standard-deviation triangle bound after the required input KS.
	// This is the author's Gaussian calibration model, not a strict tail proof.
	freshSigma := paramsLit.GLWEStdDev * math.Sqrt(float64(varianceFactor))
	k := tfhe.GaussianBoundForFailureProb(params.WorstCaseLogFailureProb())
	allowedSigmaPlain := math.Exp2(-config.CapacityBitsMeta-1) / k
	ksSigmaPlain := params.EstimateKeySwitchForBootstrapStdDev() / float64(params.Scale())
	freshSigmaPlain := freshSigma * math.Exp2(64) / float64(params.Scale())
	postKSStdDevUpper := ksSigmaPlain + freshSigmaPlain
	emit("INPUT_NOISE_MODEL", map[string]any{"variance_factor": varianceFactor, "fresh_sigma_normalized": paramsLit.GLWEStdDev, "combined_fresh_sigma_normalized": freshSigma, "fresh_sigma_plaintext": freshSigmaPlain, "estimated_KS_sigma_plaintext": ksSigmaPlain, "post_KS_sigma_triangle_bound_plaintext": postKSStdDevUpper, "allowed_pre_Meta_sigma_plaintext": allowedSigmaPlain, "within_author_capacity": postKSStdDevUpper <= allowedSigmaPlain, "strict_fullpath_tail_bound": false})
	require(postKSStdDevUpper <= allowedSigmaPlain, "online packing exceeds author's configured post-KS Gaussian capacity")
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())
	if params.RandomizedBlindRotate {
		eval.Encryptor = enc
	} // Author uses only its uniform sampler in this branch.
	lut := eval.GenLookUpTable(func(x int) int { return decodedTarget(task, x) })
	inputBytes, e := os.ReadFile(path)
	if e != nil {
		panic(e)
	}
	inputHash := sha256.Sum256(inputBytes)
	emit("META_CONFIG", map[string]any{"task_id": task, "precision": precision, "positive_half_size": half, "author_parameter": "BenchmarkMetaFBS / ParamsMetaTemplate", "author_commit": "5df59404858a0dfe5d4a361ff4934a9ffc8c3023", "capacity_bits": config.CapacityBits, "capacity_bits_meta": config.CapacityBitsMeta, "full_domain": false, "full_torus": true, "input_scale": fmt.Sprintf("2^%d", 64-precision), "input_encoding": "separate big-LWE symbols with the author full-torus scale", "output_encoding": "one big-LWE ciphertext with the same scale", "weights": weights, "positive_half_table_sha256": hex.EncodeToString(digest[:]), "input_sha256": hex.EncodeToString(inputHash[:]), "online_path": "server linear packing/sum + BootstrapLUTAssign (KS, MetaFBS, sample extraction)", "excluded": "keygen, public table construction, encryption, decryption", "setup_ms": float64(time.Since(setupStart).Nanoseconds()) / 1e6, "complete_failure_bound_established": false})
	for _, trial := range trials {
		require(len(trial.values) == len(weights), "weight/input mismatch")
		index := 0
		inputs := make([]tfhe.LWECiphertext[uint64], len(weights))
		for i, x := range trial.values {
			index += weights[i] * x
			inputs[i] = enc.EncryptLWE(x)
		}
		require(index >= 0 && index < half, "input outside positive half")
		require(decodedTarget(task, index) == trial.expected, "packing/table semantic mismatch")
		start := time.Now()
		packed := tfhe.NewLWECiphertext(params)
		packed.CopyFrom(inputs[0])
		temporary := tfhe.NewLWECiphertext(params)
		for i := 1; i < len(inputs); i++ {
			eval.ScalarMulLWEAssign(inputs[i], uint64(weights[i]), temporary)
			eval.AddLWEAssign(packed, temporary, packed)
		}
		output := tfhe.NewLWECiphertext(params)
		eval.BootstrapLUTAssign(packed, lut, output)
		ms := float64(time.Since(start).Nanoseconds()) / 1e6
		actual := enc.DecryptLWE(output)
		emit("TRIAL", map[string]any{"task_id": task, "phase": trial.phase, "index": trial.index, "inputs": trial.values, "expected": trial.expected, "actual": actual, "kind": trial.kind, "elapsed_ms": ms, "correct": actual == trial.expected})
		require(actual == trial.expected, "decrypted output mismatch; retain failed attempt")
	}
	emit("COMPLETE", map[string]any{"task_id": task, "warmups": 5, "measured": 30, "correct": 35})
}
