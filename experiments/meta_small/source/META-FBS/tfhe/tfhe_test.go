package tfhe_test

import (
	"bufio"
	"bytes"
	"fmt"
	"math"
	"os"
	"testing"

	"github.com/sp301415/tfhe-go/math/num"
	"github.com/sp301415/tfhe-go/math/poly"
	"github.com/sp301415/tfhe-go/math/vec"
	"github.com/sp301415/tfhe-go/tfhe"
	"github.com/stretchr/testify/assert"
)

var (
	params = tfhe.ParamsUint3.Compile()
	enc    = tfhe.NewEncryptor(params)
	pkEnc  = tfhe.NewPublicEncryptor(params, enc.GenPublicKey())
	eval   = tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

	paramsList = []tfhe.ParametersLiteral[uint64]{
		tfhe.ParamsUint2,
		tfhe.ParamsUint3,
		tfhe.ParamsUint4,
		tfhe.ParamsUint5,
		tfhe.ParamsUint6,
		tfhe.ParamsUint7,
		// tfhe.ParamsUint8,
	}
)

func TestParams(t *testing.T) {
	for _, params := range paramsList {
		t.Run(fmt.Sprintf("Compile/ParamsUint%v", num.Log2(params.MessageModulus)), func(t *testing.T) {
			assert.NotPanics(t, func() { params.Compile() })
		})
	}

	for _, params := range paramsList {
		t.Run(fmt.Sprintf("FailureProbability/ParamsUint%v", num.Log2(params.MessageModulus)), func(t *testing.T) {
			assert.LessOrEqual(t, math.Log2(params.Compile().EstimateFailureProbability()), -64.0)
		})
	}
}

func TestEncryptor(t *testing.T) {
	messages := []int{1, 2, 3}
	gadgetParams := params.KeySwitchParameters()

	t.Run("LWE", func(t *testing.T) {
		for _, m := range messages {
			ct := enc.EncryptLWE(m)
			assert.Equal(t, m, enc.DecryptLWE(ct))
		}
	})

	t.Run("PublicLWE", func(t *testing.T) {
		for _, m := range messages {
			ct := pkEnc.EncryptLWE(m)
			assert.Equal(t, m, enc.DecryptLWE(ct))
		}
	})

	t.Run("Lev", func(t *testing.T) {
		for _, m := range messages {
			ct := enc.EncryptLev(m, gadgetParams)
			assert.Equal(t, m, enc.DecryptLev(ct))
		}
	})

	t.Run("GSW", func(t *testing.T) {
		for _, m := range messages {
			ct := enc.EncryptGSW(m, gadgetParams)
			assert.Equal(t, m, enc.DecryptGSW(ct))
		}
	})

	t.Run("GLWE", func(t *testing.T) {
		ct := enc.EncryptGLWE(messages)
		assert.Equal(t, messages, enc.DecryptGLWE(ct)[:len(messages)])
	})

	t.Run("PublicGLWE", func(t *testing.T) {
		ct := pkEnc.EncryptGLWE(messages)
		assert.Equal(t, messages, enc.DecryptGLWE(ct)[:len(messages)])
	})

	t.Run("GLev", func(t *testing.T) {
		ct := enc.EncryptGLev(messages, gadgetParams)
		assert.Equal(t, messages, enc.DecryptGLev(ct)[:len(messages)])
	})

	t.Run("GGSW", func(t *testing.T) {
		ct := enc.EncryptGGSW(messages, gadgetParams)
		assert.Equal(t, messages, enc.DecryptGGSW(ct)[:len(messages)])
	})

	t.Run("FourierGLWE", func(t *testing.T) {
		ct := enc.EncryptFourierGLWE(messages)
		assert.Equal(t, messages, enc.DecryptFourierGLWE(ct)[:len(messages)])
	})

	t.Run("PublicFourierGLWE", func(t *testing.T) {
		ct := pkEnc.EncryptFourierGLWE(messages)
		assert.Equal(t, messages, enc.DecryptFourierGLWE(ct)[:len(messages)])
	})

	t.Run("FourierGLev", func(t *testing.T) {
		ct := enc.EncryptFourierGLev(messages, gadgetParams)
		assert.Equal(t, messages, enc.DecryptFourierGLev(ct)[:len(messages)])
	})

	t.Run("FourierGGSW", func(t *testing.T) {
		ct := enc.EncryptFourierGGSW(messages, gadgetParams)
		assert.Equal(t, messages, enc.DecryptFourierGGSW(ct)[:len(messages)])
	})
}

func TestEvaluator(t *testing.T) {
	messages := []int{1, 2, 3}

	t.Run("ExternalProduct", func(t *testing.T) {
		ct := enc.EncryptGLWE(messages)

		mul := 2
		ctMul := enc.EncryptFourierGGSW([]int{mul}, params.KeySwitchParameters())

		ctOut := eval.ExternalProductGLWE(ctMul, ct)

		for i, m := range messages {
			assert.Equal(t, mul*m, enc.DecryptGLWE(ctOut)[i])
		}
	})

	t.Run("CMUX", func(t *testing.T) {
		messagesPool := [][]int{messages, vec.Reverse(messages)}

		for _, i := range []int{0, 1} {
			ct0 := enc.EncryptGLWE(messagesPool[0])
			ct1 := enc.EncryptGLWE(messagesPool[1])
			ctGGSW := enc.EncryptFourierGGSW([]int{i}, params.BlindRotateParameters())

			ctOut := eval.CMux(ctGGSW, ct0, ct1)

			assert.Equal(t, messagesPool[i], enc.DecryptGLWE(ctOut)[:len(messages)])
		}
	})

	t.Run("KeySwitch", func(t *testing.T) {
		kskGLWEParams := tfhe.GadgetParametersLiteral[uint64]{
			Base:  1 << 12,
			Level: 3,
		}.Compile()

		encOut := tfhe.NewEncryptor(params)

		ctLWEIn := enc.EncryptLWE(messages[0])
		ctGLWEIn := enc.EncryptGLWE(messages)

		kskLWE := encOut.GenLWEKeySwitchKey(enc.DefaultLWESecretKey(), params.KeySwitchParameters())
		kskGLWE := encOut.GenGLWEKeySwitchKey(enc.SecretKey.GLWEKey, kskGLWEParams)

		ctLWEOut := eval.KeySwitchLWE(ctLWEIn, kskLWE)
		ctGLWEOut := eval.KeySwitchGLWE(ctGLWEIn, kskGLWE)

		assert.Equal(t, messages[0], encOut.DecryptLWE(ctLWEOut))
		assert.Equal(t, messages, encOut.DecryptGLWE(ctGLWEOut)[:len(messages)])
	})

	t.Run("BootstrapOriginalFunc", func(t *testing.T) {
		f := func(x int) int { return 2 * x }

		paramsOriginal := params.Literal().WithBlockSize(1).Compile()
		evalOriginal := tfhe.NewEvaluator(paramsOriginal, eval.EvaluationKey)

		for _, m := range messages {
			ct := enc.EncryptLWE(m)
			ctOut := evalOriginal.BootstrapFunc(ct, f)
			assert.Equal(t, f(m), enc.DecryptLWE(ctOut))
		}
	})

	t.Run("BootstrapBlockFunc", func(t *testing.T) {
		f := func(x int) int { return 2 * x }

		for _, m := range messages {
			ct := enc.EncryptLWE(m)
			ctOut := eval.BootstrapFunc(ct, f)
			assert.Equal(t, f(m), enc.DecryptLWE(ctOut))
		}
	})

	t.Run("BootstrapExtendedFunc", func(t *testing.T) {
		f := func(x int) int { return 2 * x }

		paramsExtended := params.Literal().WithLookUpTableSize(params.PolyDegree() << 1).Compile()
		extendedEvaluator := tfhe.NewEvaluator(paramsExtended, eval.EvaluationKey)

		for _, m := range messages {
			ct := enc.EncryptLWE(m)
			ctOut := extendedEvaluator.BootstrapFunc(ct, f)
			assert.Equal(t, f(m), enc.DecryptLWE(ctOut))
		}
	})
}

func TestMarshal(t *testing.T) {
	var n int64
	var err error
	var buf bytes.Buffer

	t.Run("Parameters", func(t *testing.T) {
		var paramsIn, paramsOut tfhe.Parameters[uint64]

		paramsIn = params
		n, err := paramsIn.WriteTo(&buf)
		assert.Equal(t, int(n), paramsIn.ByteSize())
		assert.NoError(t, err)

		n, err = paramsOut.ReadFrom(&buf)
		assert.Equal(t, int(n), paramsIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, paramsIn, paramsOut)
	})

	t.Run("LWECiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.LWECiphertext[uint64]

		ctIn = enc.EncryptLWE(0)
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("LevCiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.LevCiphertext[uint64]

		ctIn = enc.EncryptLev(0, params.KeySwitchParameters())
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("GSWCiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.GSWCiphertext[uint64]

		ctIn = enc.EncryptGSW(0, params.KeySwitchParameters())
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("GLWECiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.GLWECiphertext[uint64]

		ctIn = enc.EncryptGLWE([]int{0})
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("GLevCiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.GLevCiphertext[uint64]

		ctIn = enc.EncryptGLev([]int{0}, params.KeySwitchParameters())
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("GGSWCiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.GGSWCiphertext[uint64]

		ctIn = enc.EncryptGGSW([]int{0}, params.KeySwitchParameters())
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("FourierGLWECiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.FourierGLWECiphertext[uint64]

		ctIn = enc.EncryptFourierGLWE([]int{0})
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("FourierGLevCiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.FourierGLevCiphertext[uint64]

		ctIn = enc.EncryptFourierGLev([]int{0}, params.KeySwitchParameters())
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("FourierGGSWCiphertext", func(t *testing.T) {
		var ctIn, ctOut tfhe.FourierGGSWCiphertext[uint64]

		ctIn = enc.EncryptFourierGGSW([]int{0}, params.KeySwitchParameters())
		n, err = ctIn.WriteTo(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		n, err = ctOut.ReadFrom(&buf)
		assert.Equal(t, int(n), ctIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, ctIn, ctOut)
	})

	t.Run("SecretKey", func(t *testing.T) {
		var skIn, skOut tfhe.SecretKey[uint64]

		skIn = enc.GenSecretKey()
		n, err = skIn.WriteTo(&buf)
		assert.Equal(t, int(n), skIn.ByteSize())
		assert.NoError(t, err)

		n, err = skOut.ReadFrom(&buf)
		assert.Equal(t, int(n), skIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, skIn, skOut)
	})

	t.Run("PublicKey", func(t *testing.T) {
		var pkIn, pkOut tfhe.PublicKey[uint64]

		pkIn = enc.GenPublicKey()
		n, err = pkIn.WriteTo(&buf)
		assert.Equal(t, int(n), pkIn.ByteSize())
		assert.NoError(t, err)

		n, err = pkOut.ReadFrom(&buf)
		assert.Equal(t, int(n), pkIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, pkIn, pkOut)
	})

	t.Run("EvaluationKey", func(t *testing.T) {
		var evkIn, evkOut tfhe.EvaluationKey[uint64]

		evkIn = eval.EvaluationKey
		n, err = evkIn.WriteTo(&buf)
		assert.Equal(t, int(n), evkIn.ByteSize())
		assert.NoError(t, err)

		n, err = evkOut.ReadFrom(&buf)
		assert.Equal(t, int(n), evkIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, evkIn, evkOut)
	})

	t.Run("GLWEKeySwitchKey", func(t *testing.T) {
		var kskIn, kskOut tfhe.GLWEKeySwitchKey[uint64]

		kskIn = enc.GenGLWEKeySwitchKey(enc.SecretKey.GLWEKey, params.KeySwitchParameters())
		n, err = kskIn.WriteTo(&buf)
		assert.Equal(t, int(n), kskIn.ByteSize())
		assert.NoError(t, err)

		n, err = kskOut.ReadFrom(&buf)
		assert.Equal(t, int(n), kskIn.ByteSize())
		assert.NoError(t, err)

		assert.Equal(t, kskIn, kskOut)
	})
}

func BenchmarkEvaluationKeyGen(b *testing.B) {
	for _, params := range paramsList {
		params := params.Compile()
		enc := tfhe.NewEncryptor(params)

		b.Run(fmt.Sprintf("prec=%v", num.Log2(params.MessageModulus())), func(b *testing.B) {
			for i := 0; i < b.N; i++ {
				enc.GenEvaluationKeyParallel()
			}
		})
	}
}

func BenchmarkProgrammableBootstrap(b *testing.B) {
	for _, params := range paramsList {
		params := params.Compile()
		enc := tfhe.NewEncryptor(params)
		eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

		ct := enc.EncryptLWE(0)
		ctOut := ct.Copy()
		lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

		b.Run(fmt.Sprintf("prec=%v", num.Log2(params.MessageModulus())), func(b *testing.B) {
			for i := 0; i < b.N; i++ {
				eval.BootstrapLUTAssign(ct, lut, ctOut)
			}
		})
	}
}

// func BenchmarkApproximateEuclideanDivision(b *testing.B) {
// 	params := tfhe.ParamsUint7.Compile()
// 	enc := tfhe.NewEncryptor(params)
// 	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

// 	ct := enc.EncryptLWE(0)
// 	b.Run("Approximate Euclidean Division", func(b *testing.B) {
// 		for i := 0; i < b.N; i++ {
// 			eval.ApproximateEuclideanDivision(ct, 64, 16)
// 		}
// 	})
// }

func BenchmarkPBSwithEBS(b *testing.B) {
	for i := 8; i <= 10; i++ {
		paramsLit := tfhe.ParamsEBSTemplate
		paramsLit.MessageModulus <<= (i - 8)
		paramsLit.LookUpTableSize = tfhe.EBSLogModulusToLUTSizeMap[i]
		config := tfhe.DefaultSweepConfig()
		config.CapacityBits = 0.5
		params, err := tfhe.SweepParameter(paramsLit, config)
		if err != nil {
			panic(fmt.Sprintf("i = %d: %s", i, err))
		}
		fmt.Printf("%+v\n", params)
		tfhe.PrintParamsNoiseLevel(params, config)
		enc := tfhe.NewEncryptor(params)
		eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

		ctIn := enc.EncryptLWE(0)
		ctOut := tfhe.NewLWECiphertext(params)
		lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

		b.Run(fmt.Sprintf("PBSwithEBS/%d bits", i), func(b *testing.B) {
			for range 100 {
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			}
			for b.Loop() {
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			}
		})
	}
}
func BenchmarkPBSwithEBS2(b *testing.B) {
	for i := 11; i <= 12; i++ {
		paramsLit := tfhe.ParamsEBSTemplate
		paramsLit.MessageModulus <<= (i - 8)
		paramsLit.LookUpTableSize = tfhe.EBSLogModulusToLUTSizeMap[i]
		config := tfhe.DefaultSweepConfig()
		config.CapacityBits = 0.5
		params, err := tfhe.SweepParameter(paramsLit, config)
		if err != nil {
			panic(fmt.Sprintf("i = %d: %s", i, err))
		}
		fmt.Printf("%+v\n", params)
		tfhe.PrintParamsNoiseLevel(params, config)
		enc := tfhe.NewEncryptor(params)
		eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

		ctIn := enc.EncryptLWE(0)
		ctOut := tfhe.NewLWECiphertext(params)
		lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

		b.Run(fmt.Sprintf("PBSwithEBS/%d bits", i), func(b *testing.B) {
			for range 100 {
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			}
			for b.Loop() {
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			}
		})
	}
}

func TestMetaFBSFindParams128(t *testing.T) {
	for i := 8; i <= 12; i++ {
		paramsLit := tfhe.ParamsMetaTemplate
		paramsLit.MessageModulus <<= (i - 8)
		paramsLit = paramsLit.WithWorstCaseLogFailureProb(-130)
		config := tfhe.DefaultSweepConfig()

		config.CapacityBitsMetaBegin = 0.1
		config.CapacityBitsMetaEnd = 5
		config.CapacityBitsMetaStep = 0.01
		tfhe.SweepParameterAuto(paramsLit, &config)
	}
}

func TestMetaFBSFindParams64(t *testing.T) {
	for i := 8; i <= 12; i++ {
		paramsLit := tfhe.ParamsMetaTemplate
		paramsLit.MessageModulus <<= (i - 8)
		config := tfhe.DefaultSweepConfig()
		config.CapacityBits = tfhe.MetaFBSCapacityBits[i]

		config.CapacityBitsMetaBegin = 0.1
		config.CapacityBitsMetaEnd = 5
		config.CapacityBitsMetaStep = 0.01
		tfhe.SweepParameterAuto(paramsLit, &config)
	}
}

func TestMetaWoPPBS8n8C_128(t *testing.T) {
	{ // Meta_8, 2.28, 8
		paramsLit := tfhe.ParamsUint8FullMetaFDFB
		paramsLit.TargetRedundancyInExtraction = 1
		paramsLit.WorstCaseLogFailureProb = -130
		config := tfhe.DefaultSweepConfig()
		logGadgetBases := make([]int, 10)
		config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) +
			math.Log2(math.Sqrt(50000))

		config.CapacityBitsMetaBegin = 0.1
		config.CapacityBitsMetaEnd = 5
		config.CapacityBitsMetaStep = 0.01
		config.RequiredExtractionRedundancyBegin = 0
		config.RequiredExtractionRedundancyEnd = 40
		params := tfhe.SweepParameterAuto(paramsLit, &config)
		fmt.Printf("Best Meta8: %+v\n", params)
	}
	{ // Meta_8C, 2.28, 8
		paramsLit := tfhe.ParamsUint8FullMetaFDFB
		paramsLit.TargetRedundancyInExtraction = 1
		paramsLit.WorstCaseLogFailureProb = -130
		config := tfhe.DefaultSweepConfig()
		logGadgetBases := make([]int, 10)
		config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) +
			math.Log2(math.Sqrt(1800))

		config.CapacityBitsMetaBegin = 0.1
		config.CapacityBitsMetaEnd = 5
		config.CapacityBitsMetaStep = 0.01
		config.RequiredExtractionRedundancyBegin = 0
		config.RequiredExtractionRedundancyEnd = 40
		params := tfhe.SweepParameterAuto(paramsLit, &config)
		fmt.Printf("Best Meta8C: %+v\n", params)
	}
}

func TestMetaWoPPBS8n8C_40(t *testing.T) {
	{ // Meta_8, 2.18, 3
		paramsLit := tfhe.ParamsUint8FullMetaFDFB
		paramsLit.TargetRedundancyInExtraction = 1
		config := tfhe.DefaultSweepConfig()
		logGadgetBases := make([]int, 10)
		config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) +
			math.Log2(math.Sqrt(25000))

		config.CapacityBitsMetaBegin = 0.1
		config.CapacityBitsMetaEnd = 5
		config.CapacityBitsMetaStep = 0.01
		config.RequiredExtractionRedundancyBegin = 0
		config.RequiredExtractionRedundancyEnd = 40
		params := tfhe.SweepParameterAuto(paramsLit, &config)
		fmt.Printf("Best Meta8: %+v\n", params)
	}
	{ // Meta_8C, 2.13, 0
		paramsLit := tfhe.ParamsUint8FullMetaFDFB
		paramsLit.TargetRedundancyInExtraction = 1
		config := tfhe.DefaultSweepConfig()
		logGadgetBases := make([]int, 10)
		config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) +
			math.Log2(math.Sqrt(290))

		config.CapacityBitsMetaBegin = 0.1
		config.CapacityBitsMetaEnd = 5
		config.CapacityBitsMetaStep = 0.01
		config.RequiredExtractionRedundancyBegin = 0
		config.RequiredExtractionRedundancyEnd = 40
		params := tfhe.SweepParameterAuto(paramsLit, &config)
		fmt.Printf("Best Meta8C: %+v\n", params)
	}
}

func TestNTS25FindParams64(t *testing.T) {
	i := 12
	paramsLit := tfhe.ParamsMetaTemplate
	// we use n = 1170 instead of n = 834 from NTS25
	// because otherwise SweepParameterAuto fails to find the satisfying parameters
	// paramsLit.LWEDimension = 834
	// paramsLit.LWEStdDev = 3.6e-6
	paramsLit.MessageModulus <<= (i - 8)
	paramsLit.IsDummyPublicFunctionalKeySwitch = true

	config := tfhe.DefaultSweepConfig()
	config.CapacityBitsMetaBegin = 0.1
	config.CapacityBitsMetaEnd = 5
	config.CapacityBitsMetaStep = 0.01
	// capBitsMeta = 1.40
	tfhe.SweepParameterAuto(paramsLit, &config)
}

func TestMetaFBS(t *testing.T) {
	fastFlag := true
	// 64-bit failure probability
	for i := 8; i <= 12; i++ {
		paramsLit := tfhe.ParamsMetaTemplate
		paramsLit.MessageModulus <<= (i - 8)
		config := tfhe.DefaultSweepConfig()
		config.CapacityBits = tfhe.MetaFBSCapacityBits[i]
		config.CapacityBitsMeta = tfhe.MetaFBSCapacityBitsMeta[i]
		params, err := tfhe.SweepParameter(paramsLit, config)
		if err != nil {
			panic(fmt.Sprintf("i = %d: %s; 64 bit", i, err))
		}

		fmt.Printf("%+v\n", params)
		tfhe.PrintParamsNoiseLevel(params, config)
		enc := tfhe.NewEncryptor(params)
		eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

		ctIn := enc.EncryptLWE(0)
		ctOut := tfhe.NewLWECiphertext(params)
		lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

		if eval.Parameters.RandomizedBlindRotate {
			eval.Encryptor = enc // borrow uniform sampler for randomized BR
		}

		var msgSet []uint64 = nil
		if fastFlag {
			msgSet = []uint64{0, 1, 2, 3, paramsLit.MessageModulus - 1, paramsLit.MessageModulus - 2, paramsLit.MessageModulus - 3}
		} else {
			msgSet = make([]uint64, paramsLit.MessageModulus)
			for i := range msgSet {
				msgSet[i] = uint64(i)
			}
		}

		for _, msg := range msgSet {
			ctIn = enc.EncryptLWE(int(msg))
			ctOut = tfhe.NewLWECiphertext(params)
			lut = eval.GenLookUpTable(func(x int) int { return 2*x + 1 })
			eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			gotMsg := uint64(enc.DecryptLWE(ctOut)) % paramsLit.MessageModulus
			expMsg := (2*msg + 1) % paramsLit.MessageModulus
			if msg >= paramsLit.MessageModulus/2 {
				expMsg = -(2*(msg-paramsLit.MessageModulus/2) + 1) % paramsLit.MessageModulus
			}
			if gotMsg != expMsg {
				t.Fatalf("64 bit: i = %d, x = %d, expecting %d, got %d\n", i, msg, expMsg, gotMsg)
			}
			// fmt.Printf("%d --> %d (%d)\n", msg, gotMsg, expMsg)
		}
	}
	// 128-bit failure probability
	for i := 8; i <= 12; i++ {
		paramsLit := tfhe.ParamsMetaTemplate
		paramsLit.MessageModulus <<= (i - 8)
		paramsLit = paramsLit.WithWorstCaseLogFailureProb(-130)
		config := tfhe.DefaultSweepConfig()
		config.CapacityBitsMeta = 0.5
		params, err := tfhe.SweepParameter(paramsLit, config)
		if err != nil {
			panic(fmt.Sprintf("i = %d: %s; 128 bit", i, err))
		}

		fmt.Printf("%+v\n", params)
		tfhe.PrintParamsNoiseLevel(params, config)
		enc := tfhe.NewEncryptor(params)
		eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

		ctIn := enc.EncryptLWE(0)
		ctOut := tfhe.NewLWECiphertext(params)
		lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

		if eval.Parameters.RandomizedBlindRotate {
			eval.Encryptor = enc // borrow uniform sampler for randomized BR
		}

		var msgSet []uint64 = nil
		if fastFlag {
			msgSet = []uint64{0, 1, 2, 3, paramsLit.MessageModulus - 1, paramsLit.MessageModulus - 2, paramsLit.MessageModulus - 3}
		} else {
			msgSet = make([]uint64, paramsLit.MessageModulus)
			for i := range msgSet {
				msgSet[i] = uint64(i)
			}
		}

		for _, msg := range msgSet {
			ctIn = enc.EncryptLWE(int(msg))
			ctOut = tfhe.NewLWECiphertext(params)
			lut = eval.GenLookUpTable(func(x int) int { return 2*x + 1 })
			eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			gotMsg := uint64(enc.DecryptLWE(ctOut)) % paramsLit.MessageModulus
			expMsg := (2*msg + 1) % paramsLit.MessageModulus
			if msg >= paramsLit.MessageModulus/2 {
				expMsg = -(2*(msg-paramsLit.MessageModulus/2) + 1) % paramsLit.MessageModulus
			}
			if gotMsg != expMsg {
				t.Fatalf("128 bit: i = %d, x = %d, expecting %d, got %d\n", i, msg, expMsg, gotMsg)
			}
			// fmt.Printf("%d --> %d (%d)\n", msg, gotMsg, expMsg)
		}
	}
}

func BenchmarkMetaFBS(b *testing.B) {
	for i := 8; i <= 12; i++ {
		paramsLit := tfhe.ParamsMetaTemplate
		paramsLit.MessageModulus <<= (i - 8)
		config := tfhe.DefaultSweepConfig()
		config.CapacityBits = tfhe.MetaFBSCapacityBits[i]
		config.CapacityBitsMeta = tfhe.MetaFBSCapacityBitsMeta[i]
		params, err := tfhe.SweepParameter(paramsLit, config)
		if err != nil {
			panic(fmt.Sprintf("i = %d: %s", i, err))
		}
		// DEBUG: record bootstrapping noise distribution
		debug_dist := false
		debug_cnt := 100000
		debug_output_filename := "/home/msh/HE/meta_fbs/logs/dist-9bits-all-fixbr-%d-rebuttal.txt"
		/*
			~/HE/meta_fbs/logs/dist-final-9bits-all-newbr-%d.txt"
			~/HE/meta_fbs/logs/dist-final-9bits-all-fixbr-%d.txt"
			~/HE/meta_fbs/logs/dist-final-9bits-all-oldbr-%d.txt"
			~/HE/meta_fbs/logs/dist-final-9bits-bronly-newbr-%d.txt"
			~/HE/meta_fbs/logs/dist-final-9bits-bronly-fixbr-%d.txt"
			~/HE/meta_fbs/logs/dist-final-9bits-bronly-oldbr-%d.txt"
			~/HE/meta_fbs/logs/tmp-%d.txt"
		*/
		fmt.Printf("%+v\n", params)
		tfhe.PrintParamsNoiseLevel(params, config)
		enc := tfhe.NewEncryptor(params)
		eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

		ctIn := enc.EncryptLWE(0)
		ctOut := tfhe.NewLWECiphertext(params)
		lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

		if eval.Parameters.RandomizedBlindRotate {
			eval.Encryptor = enc // borrow uniform sampler for randomized BR
		}
		if debug_dist {
			f, _ := os.Create(fmt.Sprintf(debug_output_filename, debug_cnt))
			w := bufio.NewWriterSize(f, 100000)
			for i := range debug_cnt {
				enc.EncryptLWEAssign(0, ctIn)
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
				res := enc.DecryptLWEPhase(ctOut)

				fmt.Fprintf(w, "%d ", (int64(res.Value)<<9)>>9) // get the noise
				if i%100 == 0 {
					w.Flush() // forces auto-flush after each write
				}
			}
			w.Flush()
			f.Close()
			return
		}
		b.Run(fmt.Sprintf("PBSwithEBS/%d bits", i), func(b *testing.B) {
			for range 100 {
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			}
			for b.Loop() {
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			}
		})
	}
}
func BenchmarkMetaFBS128(b *testing.B) {
	for i := 8; i <= 12; i++ {
		paramsLit := tfhe.ParamsMetaTemplate
		paramsLit.MessageModulus <<= (i - 8)
		paramsLit = paramsLit.WithWorstCaseLogFailureProb(-130)
		config := tfhe.DefaultSweepConfig()
		config.CapacityBits = tfhe.MetaFBSCapacityBits[i]
		config.CapacityBitsMeta = tfhe.MetaFBSCapacityBitsMeta128[i]
		params, err := tfhe.SweepParameter(paramsLit, config)
		if err != nil {
			panic(fmt.Sprintf("i = %d: %s", i, err))
		}
		fmt.Printf("%+v\n", params)
		tfhe.PrintParamsNoiseLevel(params, config)
		enc := tfhe.NewEncryptor(params)
		eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

		ctIn := enc.EncryptLWE(0)
		ctOut := tfhe.NewLWECiphertext(params)
		lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

		if eval.Parameters.RandomizedBlindRotate {
			eval.Encryptor = enc // borrow uniform sampler for randomized BR
		}
		b.Run(fmt.Sprintf("PBSwithEBS128/%d bits", i), func(b *testing.B) {
			for range 100 {
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			}
			for b.Loop() {
				eval.BootstrapLUTAssign(ctIn, lut, ctOut)
			}
		})
	}
}

func BenchmarkNTS25(b *testing.B) {
	// based on Meta-PBS parameters
	i := 12
	paramsLit := tfhe.ParamsMetaTemplate
	paramsLit.MessageModulus <<= (i - 8)
	paramsLit.IsDummyPublicFunctionalKeySwitch = true
	config := tfhe.DefaultSweepConfig()
	config.CapacityBits = 0.5
	config.CapacityBitsMeta = 1.40 // found using TestNTS25FindParams40
	params, err := tfhe.SweepParameter(paramsLit, config)
	if err != nil {
		panic(fmt.Sprintf("i = %d: %s", i, err))
	}

	fmt.Printf("%+v\n", params)
	tfhe.PrintParamsNoiseLevel(params, config)
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())
	if eval.Parameters.RandomizedBlindRotate {
		eval.Encryptor = enc // borrow uniform sampler for randomized BR
	}

	ctIn := enc.EncryptLWE(0)
	ctShort := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	ctACC := tfhe.NewGLWECiphertext(params)
	lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

	b.Run(fmt.Sprintf("NTS25 simulated/%d bits (bootstrap 1 out of 4)", i), func(b *testing.B) {
		for range 100 {
			eval.BlindRotateAssign(ctIn, lut, ctACC)
		}
		for b.Loop() {
			eval.BlindRotateAssign(ctIn, lut, ctACC)
		}
	})

	// W0 = 4, W1 = 3,   W2 = 3,  W3 = 2   (L = 4)
	// D0 = 8, D1 = 5,   D2 = 2            (Di = sum_{l=i+1}^{L-1}Wl)
	//         S1 = 512, S2 = 96, S3 = 16  (Si = (i+1)*2^D_{i-1})
	// a total of 624 LWE keyswitching for SE
	b.Run(fmt.Sprintf("NTS25 simulated/%d bits (SE 12 out of 624)", i), func(b *testing.B) {
		for range 100 {
			eval.KeySwitchForBootstrapAssign(ctIn, ctShort)
		}
		for b.Loop() {
			for range 12 {
				eval.KeySwitchForBootstrapAssign(ctIn, ctShort)
			}
		}
	})

	polys := make([]poly.Poly[uint64], params.LWEDimension())
	for i := range params.LWEDimension() {
		enc.UniformSampler.SamplePolyAssign(polys[i])
	}
	b.Run(fmt.Sprintf("NTS25 simulated/%d bits (PKS 1 out of 3)", i), func(b *testing.B) {
		for range 100 {
			eval.PublicFunctionalKeySwitchFourierDummy(polys, ctACC)
		}
		for b.Loop() {
			eval.PublicFunctionalKeySwitchFourierDummy(polys, ctACC)
		}
	})
}

func BenchmarkThreeBR(b *testing.B) {
	paramsLit := tfhe.ParamsThreeBR
	params := paramsLit.Compile()
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

	fmt.Printf("%f\n", params.EstimateBlindRotateStdDev())

	ctIn := enc.EncryptLWE(0)
	ctOut := tfhe.NewLWECiphertextCustom[uint64](params.GLWEDimension())
	lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

	distCnt := 100000
	f, _ := os.Create(fmt.Sprintf("/home/msh/HE/meta_fbs/logs/dist-final-try-threebr-newbr-exact-noasm-%d.txt", distCnt))

	w := bufio.NewWriter(f)

	acc1, acc2, acc3 := tfhe.NewGLWECiphertext(params), tfhe.NewGLWECiphertext(params), tfhe.NewGLWECiphertext(params)
	for i := range distCnt {
		enc.EncryptLWEAssign(0, ctIn)
		ctQuo, ctRem, curLogQ := eval.ApproximateEuclideanDivision(ctIn, 64, 1<<12)
		for j := range params.LWEDimension() {
			ctQuo.Value[j] <<= (64 - 12)
		}
		eval.BlindRotateAssign(ctIn, lut, acc1)

		ctQuo, ctRem, curLogQ = eval.ApproximateEuclideanDivision(ctRem, curLogQ, 5)
		for j := range params.LWEDimension() {
			ctQuo.Value[j] <<= (64 - 12)
		}
		eval.BlindRotateCiphertextAssign(ctQuo, acc1, acc2)

		ctQuo, ctRem, curLogQ = eval.ApproximateEuclideanDivision(ctRem, curLogQ, 4)
		for j := range params.LWEDimension() {
			ctQuo.Value[j] <<= (64 - 12)
		}
		eval.BlindRotateCiphertextAssign(ctQuo, acc2, acc3)
		acc3.ToLWECiphertextAssign(0, ctOut)

		res := enc.DecryptLWEPhase(ctOut)

		fmt.Fprintf(w, "%d ", (int64(res.Value)<<9)>>9)
		if i%100 == 0 {
			w.Flush() // forces auto-flush after each write
		}
	}
	w.Flush()
	f.Close()
}

func BenchmarkMetaUint8Compact(b *testing.B) {
	paramsLit := tfhe.ParamsUint8FullMetaFDFB
	paramsLit.TargetRedundancyInExtraction = 0
	config := tfhe.DefaultSweepConfig()
	logGadgetBases := make([]int, 10)
	config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) +
		math.Log2(math.Sqrt(290))
	config.CapacityBitsMeta = 2.13
	params, _ := tfhe.SweepParameter(paramsLit, config)
	fmt.Printf("%+v\n", params)
	tfhe.PrintParamsNoiseLevel(params, config)
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())
	if eval.Parameters.RandomizedBlindRotate {
		eval.Encryptor = enc // borrow uniform sampler for randomized BR
	}

	ctGLWEIn := enc.EncryptGLWE([]int{0})
	ctGLWEOut := tfhe.NewGLWECiphertext(params)
	ctLWEInShort := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	enc.EncryptLWEAssign(1, ctLWEInShort)
	ctLWEOutShort := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	ctLWEInLong := enc.EncryptLWE(0)
	ctLWEOutLongList := []tfhe.LWECiphertext[uint64]{tfhe.NewLWECiphertext(params), tfhe.NewLWECiphertext(params), tfhe.NewLWECiphertext(params)}
	b.Run("MetaUint8Dense/All TruncRepeat", func(b *testing.B) {
		for range 100 {
			for j := range params.CountTruncRepeats() - 1 {
				eval.TruncRepeat(ctGLWEIn, j, ctGLWEOut)
			}
			for range params.CountCancelSignLUTs() {
				eval.TruncRepeat(ctGLWEIn, params.CountTruncRepeats()-1, ctGLWEOut)
			}
		}
		for b.Loop() {
			for j := range params.CountTruncRepeats() - 1 {
				eval.TruncRepeat(ctGLWEIn, j, ctGLWEOut)
			}
			for range params.CountCancelSignLUTs() {
				eval.TruncRepeat(ctGLWEIn, params.CountTruncRepeats()-1, ctGLWEOut)
			}
		}
	})
	lut := eval.GenLookUpTable(func(x int) int { return x })
	b.Run("MetaUint8Dense/Blind Rotation (1 out of 4)", func(b *testing.B) {
		for range 100 {
			eval.BlindRotateAssign(ctLWEInShort, lut, ctGLWEOut)
		}
		for b.Loop() {
			eval.BlindRotateAssign(ctLWEInShort, lut, ctGLWEOut)
		}
	})
	b.Run("MetaUint8Dense/Keyswitch (1 out of 2)", func(b *testing.B) {
		for range 100 {
			eval.KeySwitchForBootstrapAssign(ctLWEInLong, ctLWEOutShort)
		}
		for b.Loop() {
			eval.KeySwitchForBootstrapAssign(ctLWEInLong, ctLWEOutShort)
		}
	})

	ct := enc.EncryptLWE(0)
	gadgetLength := params.CountLUTs() - 1
	gadgetfuncs := eval.GadgetFuncs(func(x int) int { return x }, gadgetLength)
	ctSgn := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	ctProd := tfhe.NewGLWECiphertext(params)
	eval.GenManyLookUpTablesAssign(append([](func(int) int){eval.SgnFunc()}, gadgetfuncs...), lut)
	lut.CountLUTs = len(gadgetfuncs) + 1
	b.Run("MetaUint8Dense/Total", func(b *testing.B) {
		for range 100 {
			eval.BootstrapFullDomainManyLUTsAssign(ct, lut, ctSgn, ctGLWEOut)
			eval.CancelSignAssign(ctSgn, ctProd, ctLWEOutLongList, 1, 4)
		}
		for b.Loop() {
			eval.BootstrapFullDomainManyLUTsAssign(ct, lut, ctSgn, ctGLWEOut)
			eval.CancelSignAssign(ctSgn, ctProd, ctLWEOutLongList, 1, 4)
		}
	})
}

func BenchmarkMetaUint8Compact128(b *testing.B) {
	paramsLit := tfhe.ParamsUint8FullMetaFDFB
	paramsLit.TargetRedundancyInExtraction = 8
	paramsLit.WorstCaseLogFailureProb = -130
	config := tfhe.DefaultSweepConfig()
	logGadgetBases := make([]int, 10)
	config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) +
		math.Log2(math.Sqrt(1800))
	config.CapacityBitsMeta = 2.28
	params, _ := tfhe.SweepParameter(paramsLit, config)
	fmt.Printf("%+v\n", params)
	tfhe.PrintParamsNoiseLevel(params, config)
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())
	if eval.Parameters.RandomizedBlindRotate {
		eval.Encryptor = enc // borrow uniform sampler for randomized BR
	}

	ctGLWEOut := tfhe.NewGLWECiphertext(params)
	ctLWEInShort := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	enc.EncryptLWEAssign(1, ctLWEInShort)
	ctLWEOutLongList := []tfhe.LWECiphertext[uint64]{tfhe.NewLWECiphertext(params), tfhe.NewLWECiphertext(params), tfhe.NewLWECiphertext(params)}

	lut := eval.GenLookUpTable(func(x int) int { return x })
	ct := enc.EncryptLWE(0)
	gadgetLength := params.CountLUTs() - 1
	gadgetfuncs := eval.GadgetFuncs(func(x int) int { return x }, gadgetLength)
	ctSgn := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	ctProd := tfhe.NewGLWECiphertext(params)
	eval.GenManyLookUpTablesAssign(append([](func(int) int){eval.SgnFunc()}, gadgetfuncs...), lut)
	lut.CountLUTs = len(gadgetfuncs) + 1
	b.Run("MetaUint8C-128/Total", func(b *testing.B) {
		for range 100 {
			eval.BootstrapFullDomainManyLUTsAssign(ct, lut, ctSgn, ctGLWEOut)
			eval.CancelSignAssign(ctSgn, ctProd, ctLWEOutLongList, 1, 4)
		}
		for b.Loop() {
			eval.BootstrapFullDomainManyLUTsAssign(ct, lut, ctSgn, ctGLWEOut)
			eval.CancelSignAssign(ctSgn, ctProd, ctLWEOutLongList, 1, 4)
		}
	})
}

func BenchmarkMetaUint8_128(b *testing.B) {
	paramsLit := tfhe.ParamsUint8FullMetaFDFB
	paramsLit.TargetRedundancyInExtraction = 8
	paramsLit.WorstCaseLogFailureProb = -130
	config := tfhe.DefaultSweepConfig()
	logGadgetBases := make([]int, 10)
	config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) +
		math.Log2(math.Sqrt(50000))
	config.CapacityBitsMeta = 2.28
	params, _ := tfhe.SweepParameter(paramsLit, config)
	fmt.Printf("%+v\n", params)
	tfhe.PrintParamsNoiseLevel(params, config)
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())
	if eval.Parameters.RandomizedBlindRotate {
		eval.Encryptor = enc // borrow uniform sampler for randomized BR
	}

	ctGLWEOut := tfhe.NewGLWECiphertext(params)
	ctLWEInShort := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	enc.EncryptLWEAssign(1, ctLWEInShort)
	ctLWEOutLongList := []tfhe.LWECiphertext[uint64]{tfhe.NewLWECiphertext(params), tfhe.NewLWECiphertext(params), tfhe.NewLWECiphertext(params)}

	lut := eval.GenLookUpTable(func(x int) int { return x })
	ct := enc.EncryptLWE(0)
	gadgetLength := params.CountLUTs() - 1
	gadgetfuncs := eval.GadgetFuncs(func(x int) int { return x }, gadgetLength)
	ctSgn := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	ctProd := tfhe.NewGLWECiphertext(params)
	eval.GenManyLookUpTablesAssign(append([](func(int) int){eval.SgnFunc()}, gadgetfuncs...), lut)
	lut.CountLUTs = len(gadgetfuncs) + 1
	b.Run("MetaUint8-128/Total", func(b *testing.B) {
		for range 100 {
			eval.BootstrapFullDomainManyLUTsAssign(ct, lut, ctSgn, ctGLWEOut)
			eval.CancelSignAssign(ctSgn, ctProd, ctLWEOutLongList, 1, 4)
		}
		for b.Loop() {
			eval.BootstrapFullDomainManyLUTsAssign(ct, lut, ctSgn, ctGLWEOut)
			eval.CancelSignAssign(ctSgn, ctProd, ctLWEOutLongList, 1, 4)
		}
	})
}

func BenchmarkMetaUint8(b *testing.B) {
	paramsLit := tfhe.ParamsUint8FullMetaFDFB
	paramsLit.TargetRedundancyInExtraction = 3
	config := tfhe.DefaultSweepConfig()
	logGadgetBases := make([]int, 10)
	config.CapacityBits = paramsLit.Compile().CapacityForGadgetMultAssign(paramsLit.CountLUTs-1, logGadgetBases) +
		math.Log2(math.Sqrt(25000))
	config.CapacityBitsMeta = 2.18
	params, _ := tfhe.SweepParameter(paramsLit, config)
	fmt.Printf("%+v\n", params)
	tfhe.PrintParamsNoiseLevel(params, config)
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())
	if eval.Parameters.RandomizedBlindRotate {
		eval.Encryptor = enc // borrow uniform sampler for randomized BR
	}

	ctGLWEIn := enc.EncryptGLWE([]int{0})
	ctGLWEOut := tfhe.NewGLWECiphertext(params)
	ctLWEInShort := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	enc.EncryptLWEAssign(1, ctLWEInShort)
	ctLWEOutShort := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	ctLWEInLong := enc.EncryptLWE(0)
	ctLWEOutLongList := []tfhe.LWECiphertext[uint64]{tfhe.NewLWECiphertext(params), tfhe.NewLWECiphertext(params), tfhe.NewLWECiphertext(params)}
	b.Run("MetaUint8Dense/All TruncRepeat", func(b *testing.B) {
		for range 100 {
			for j := range params.CountTruncRepeats() - 1 {
				eval.TruncRepeat(ctGLWEIn, j, ctGLWEOut)
			}
			for range params.CountCancelSignLUTs() {
				eval.TruncRepeat(ctGLWEIn, params.CountTruncRepeats()-1, ctGLWEOut)
			}
		}
		for b.Loop() {
			for j := range params.CountTruncRepeats() - 1 {
				eval.TruncRepeat(ctGLWEIn, j, ctGLWEOut)
			}
			for range params.CountCancelSignLUTs() {
				eval.TruncRepeat(ctGLWEIn, params.CountTruncRepeats()-1, ctGLWEOut)
			}
		}
	})
	lut := eval.GenLookUpTable(func(x int) int { return x })
	b.Run("MetaUint8Dense/Blind Rotation (1 out of 4)", func(b *testing.B) {
		for range 100 {
			eval.BlindRotateAssign(ctLWEInShort, lut, ctGLWEOut)
		}
		for b.Loop() {
			eval.BlindRotateAssign(ctLWEInShort, lut, ctGLWEOut)
		}
	})
	b.Run("MetaUint8Dense/Keyswitch (1 out of 2)", func(b *testing.B) {
		for range 100 {
			eval.KeySwitchForBootstrapAssign(ctLWEInLong, ctLWEOutShort)
		}
		for b.Loop() {
			eval.KeySwitchForBootstrapAssign(ctLWEInLong, ctLWEOutShort)
		}
	})

	ct := enc.EncryptLWE(0)
	gadgetLength := params.CountLUTs() - 1
	gadgetfuncs := eval.GadgetFuncs(func(x int) int { return x }, gadgetLength)
	ctSgn := tfhe.NewLWECiphertextCustom[uint64](params.LWEDimension())
	eval.GenManyLookUpTablesAssign(append([](func(int) int){eval.SgnFunc()}, gadgetfuncs...), lut)
	lut.CountLUTs = len(gadgetfuncs) + 1
	b.Run("MetaUint8Dense/Total", func(b *testing.B) {
		for range 100 {
			eval.BootstrapFullDomainManyLUTsAssign(ct, lut, ctSgn, ctGLWEOut)
			eval.CancelSignAssign(ctSgn, ctGLWEOut, ctLWEOutLongList, 1, 4)
		}
		for b.Loop() {
			eval.BootstrapFullDomainManyLUTsAssign(ct, lut, ctSgn, ctGLWEOut)
			eval.CancelSignAssign(ctSgn, ctGLWEOut, ctLWEOutLongList, 1, 4)
		}
	})
}

func BenchmarkLHEBase16(b *testing.B) {
	params := tfhe.ParamsLHEBase16.Compile()
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

	ctIn := enc.EncryptLWE(0)
	ctOut := tfhe.NewLWECiphertext(params)
	lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

	b.Run("LHE Base 16/Blind rotation with key switching (1 out of 4)", func(b *testing.B) {
		for range 100 {
			eval.BootstrapLUTAssign(ctIn, lut, ctOut)
		}
		for b.Loop() {
			eval.BootstrapLUTAssign(ctIn, lut, ctOut)
		}
	})
}

func BenchmarkLHEBase256(b *testing.B) {
	params := tfhe.ParamsLHEBase256.Compile()
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

	ctIn := enc.EncryptLWE(0)
	ctOut := tfhe.NewLWECiphertext(params)
	lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

	b.Run("LHE Base 256/Blind rotation with key switching (1 out of 4)", func(b *testing.B) {
		for range 100 {
			eval.BootstrapLUTAssign(ctIn, lut, ctOut)
		}
		for b.Loop() {
			eval.BootstrapLUTAssign(ctIn, lut, ctOut)
		}
	})
}

func BenchmarkTreeBased(b *testing.B) {
	params := tfhe.ParamsTreeBased.Compile()
	enc := tfhe.NewEncryptor(params)
	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

	ctIn := enc.EncryptLWE(0)
	ctOut := tfhe.NewLWECiphertext(params)
	ctOutGLWE := tfhe.NewGLWECiphertext(params)
	ctSumGLWE := tfhe.NewGLWECiphertext(params)
	lut := eval.GenLookUpTable(func(x int) int { return 2*x + 1 })

	b.Run("Tree Based/Blind rotation (1 out of 3)", func(b *testing.B) {
		for range 100 {
			eval.BootstrapLUTAssign(ctIn, lut, ctOut)
		}
		for b.Loop() {
			eval.BootstrapLUTAssign(ctIn, lut, ctOut)
		}
	})

	b.Run("Tree Based/Public Functional Keyswitching (1 out of 2)", func(b *testing.B) {
		for range 100 {
			for range 16 {
				eval.PublicFunctionalKeySwitchDummy(ctIn, ctOutGLWE)
				eval.AddGLWEAssign(ctOutGLWE, ctSumGLWE, ctSumGLWE)
			}
		}
		for b.Loop() {
			for range 16 {
				eval.PublicFunctionalKeySwitchDummy(ctIn, ctOutGLWE)
				eval.AddGLWEAssign(ctOutGLWE, ctSumGLWE, ctSumGLWE)
			}
		}
	})
}

func ExampleEncryptor() {
	// Parameters must be compiled before use.
	params := tfhe.ParamsUint4.Compile()

	enc := tfhe.NewEncryptor(params)

	ctLWE := enc.EncryptLWE(4)
	ctGLWE := enc.EncryptGLWE([]int{1, 2, 3, 4})

	// Decrypt Everything!
	fmt.Println(enc.DecryptLWE(ctLWE))
	fmt.Println(enc.DecryptGLWE(ctGLWE)[:4])
	// Output:
	// 4
	// [1 2 3 4]
}

func ExampleEvaluator_CMux() {
	params := tfhe.ParamsUint4.Compile()
	gadgetParams := tfhe.GadgetParametersLiteral[uint64]{
		Base:  1 << 3,
		Level: 6,
	}.Compile()

	enc := tfhe.NewEncryptor(params)

	ct0 := enc.EncryptGLWE([]int{2})
	ct1 := enc.EncryptGLWE([]int{5})
	ctFlag := enc.EncryptFourierGGSW([]int{1}, gadgetParams)

	// We don't need evaluation key for CMUX.
	eval := tfhe.NewEvaluator(params, tfhe.EvaluationKey[uint64]{})

	ctOut := eval.CMux(ctFlag, ct0, ct1)
	fmt.Println(enc.DecryptGLWE(ctOut)[0])
	// Output:
	// 5
}

func ExampleEvaluator_BootstrapFunc() {
	params := tfhe.ParamsUint4.Compile()

	enc := tfhe.NewEncryptor(params)

	ct := enc.EncryptLWE(3)

	eval := tfhe.NewEvaluator(params, enc.GenEvaluationKeyParallel())

	ctOut := eval.BootstrapFunc(ct, func(x int) int { return 2*x + 1 })
	fmt.Println(enc.DecryptLWE(ctOut))
	// Output:
	// 7
}
