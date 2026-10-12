// A common-task adapter of the author's full-domain Meta-WoP-PBS routines.
// Author library code and noise parameters are unchanged.
package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math"
	"math/bits"
	"os"
	"strconv"
	"time"

	"github.com/sp301415/tfhe-go/tfhe"
)

func emit(kind string, value any) {
	b, err := json.Marshal(value)
	if err != nil {
		panic(err)
	}
	fmt.Printf("%s %s\n", kind, b)
}
func integer(s string) int {
	v, err := strconv.Atoi(s)
	if err != nil {
		panic(err)
	}
	return v
}
func main() {
	if len(os.Args) < 5 {
		panic("usage: dccmeta div|count size predicate input.csv [max_rows]")
	}
	task, size, pred, path := os.Args[1], integer(os.Args[2]), os.Args[3], os.Args[4]
	if task == "div" && size != 16 {
		panic("full-domain adapter only supports t=16 division")
	}
	if task != "div" && task != "count" {
		panic("unknown task")
	}
	if task == "count" && size != 12 && size != 16 {
		panic("count size must be12 or16")
	}
	if task == "count" && pred != "threshold" && pred != "interval" {
		panic("unknown predicate")
	}
	f, err := os.Open(path)
	if err != nil {
		panic(err)
	}
	rows, err := csv.NewReader(f).ReadAll()
	f.Close()
	if err != nil {
		panic(err)
	}
	maxRows := len(rows) - 1
	if len(os.Args) > 5 {
		maxRows = min(maxRows, integer(os.Args[5]))
	}
	// Exactly the author's non-compact Meta_8 parameter-selection setup in
	// BenchmarkMetaUint8. In particular neither input sigma is decreased.
	paramsLit := tfhe.ParamsUint8FullMetaFDFB
	paramsLit.TargetRedundancyInExtraction = 3
	config := tfhe.DefaultSweepConfig()
	logGadgetBases := make([]int, 10)
	config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) + math.Log2(math.Sqrt(25000))
	config.CapacityBitsMeta = 2.18
	setupStart := time.Now()
	params, _ := tfhe.SweepParameter(paramsLit, config)
	fmt.Printf("AUTHOR_COMPILED_PARAMS %+v\n", params)
	tfhe.PrintParamsNoiseLevel(params, config)
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())
	if eval.Parameters.RandomizedBlindRotate {
		eval.Encryptor = enc
	}
	target := func(x int) int {
		if task == "div" {
			m, d := x&15, x>>4
			if d == 0 {
				return 0
			}
			return m / d
		}
		if x > size {
			return 0
		}
		if pred == "threshold" {
			if x >= size/2 {
				return 1
			}
			return 0
		}
		if x >= size/3 && x <= 2*size/3 {
			return 1
		}
		return 0
	}
	// Full-domain table: sign cancellation is mandatory. Only the first
	// requested result is recovered; remaining author table slots are zero.
	lut := tfhe.NewLookUpTable(params)
	eval.GenManyLookUpTablesAssign([]func(int) int{eval.SgnFunc(), target, func(int) int { return 0 }, func(int) int { return 0 }}, lut)
	lut.CountLUTs = 4
	setupMS := float64(time.Since(setupStart).Nanoseconds()) / 1e6
	varianceFactor := size
	if task == "div" {
		varianceFactor = 257
	}
	maxFreshSigma := paramsLit.GLWEStdDev * math.Sqrt(float64(varianceFactor))
	emit("META_CONFIG", map[string]any{"task": task, "size": size, "predicate": pred, "input_manifest": path, "rows": maxRows, "author_commit": "5df59404858a0dfe5d4a361ff4934a9ffc8c3023", "author_parameter": "BenchmarkMetaUint8 / Meta_8", "setup_ms": setupMS, "input_scale": "2^56", "input_encoding": "separate full-torus 8-bit big-LWE ciphertexts", "output_encoding": "full-torus 8-bit big-LWE ciphertext; value is quotient or Boolean", "fresh_input_sigma": paramsLit.GLWEStdDev, "fresh_sigma_after_online_linear_combination": maxFreshSigma, "input_noise_variance_factor": varianceFactor, "online_path": "encrypted linear packing/sum + BootstrapFullDomainManyLUTsAssign + CancelSignAssign(1,2)", "count_route": "count-statistic adapter; not a direct2^n truth-table benchmark", "single_output_recovery": true, "complete_failure_bound_established": false})
	for _, row := range rows[1 : 1+maxRows] {
		phase, index := row[0], integer(row[1])
		if integer(row[2]) != size {
			panic("size mismatch")
		}
		var inputs []tfhe.LWECiphertext[uint64]
		var expected, m, d, mask int
		if task == "div" {
			m, d = integer(row[3]), integer(row[4])
			if m < 0 || m >= 16 || d < 1 || d >= 16 {
				panic("invalid division input")
			}
			expected = m / d
			inputs = []tfhe.LWECiphertext[uint64]{enc.EncryptLWE(m), enc.EncryptLWE(d)}
		} else {
			mask = integer(row[3])
			weight := bits.OnesCount(uint(mask))
			if weight != integer(row[4]) {
				panic("weight mismatch")
			}
			expected = target(weight)
			if pred == "threshold" && expected != integer(row[5]) {
				panic("target mismatch")
			}
			if pred == "interval" && expected != integer(row[6]) {
				panic("target mismatch")
			}
			inputs = make([]tfhe.LWECiphertext[uint64], size)
			for j := range size {
				inputs[j] = enc.EncryptLWE((mask >> j) & 1)
			}
		}
		start := time.Now()
		packed := tfhe.NewLWECiphertext(params)
		if task == "div" {
			eval.ScalarMulLWEAssign(inputs[1], 16, packed)
			eval.AddLWEAssign(packed, inputs[0], packed)
		} else {
			packed.CopyFrom(inputs[0])
			for j := 1; j < size; j++ {
				eval.AddLWEAssign(packed, inputs[j], packed)
			}
		}
		ctSgn := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
		ctGLWE := tfhe.NewGLWECiphertext(params)
		ctOut := []tfhe.LWECiphertext[uint64]{tfhe.NewLWECiphertext(params)}
		eval.BootstrapFullDomainManyLUTsAssign(packed, lut, ctSgn, ctGLWE)
		eval.CancelSignAssign(ctSgn, ctGLWE, ctOut, 1, 2)
		elapsed := float64(time.Since(start).Nanoseconds()) / 1e6
		actual := enc.DecryptLWE(ctOut[0])
		ok := actual == expected
		emit("TRIAL", map[string]any{"phase": phase, "index": index, "task": task, "size": size, "predicate": pred, "m": m, "d": d, "bitmask": mask, "expected": expected, "actual": actual, "correct": ok, "elapsed_ms": elapsed})
		if !ok {
			panic("decrypted result mismatch; failed run retained")
		}
	}
}
