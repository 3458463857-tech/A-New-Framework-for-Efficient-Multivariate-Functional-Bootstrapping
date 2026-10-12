package tfhe

var (

	// ParamsBinary is a default parameter set for binary TFHE.
	ParamsBinary = ParametersLiteral[uint32]{
		LWEDimension:    687,
		GLWERank:        2,
		PolyDegree:      512,
		LookUpTableSize: 512,

		LWEStdDev:  0.00002120846893069971872305794214,
		GLWEStdDev: 0.00000002685935683878752834630074,

		BlockSize: 3,

		MessageModulus: 1 << 1,

		BlindRotateParameters: GadgetParametersLiteral[uint32]{
			Base:  1 << 6,
			Level: 3,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint32]{
			Base:  1 << 3,
			Level: 4,
		},

		BootstrapOrder: OrderBlindRotateKeySwitch,
	}

	// ParamsBinaryCompact is a parameter set for binary TFHE
	// with OrderKeySwitchBlindRotate.
	ParamsBinaryCompact = ParametersLiteral[uint32]{
		LWEDimension:    687,
		GLWERank:        2,
		PolyDegree:      512,
		LookUpTableSize: 512,

		LWEStdDev:  0.00002120846893069971872305794214,
		GLWEStdDev: 0.00000002685935683878752834630074,

		BlockSize: 3,

		MessageModulus: 1 << 1,

		BlindRotateParameters: GadgetParametersLiteral[uint32]{
			Base:  1 << 6,
			Level: 3,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint32]{
			Base:  1 << 4,
			Level: 3,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	// ParamsBinaryOriginal is a parameter set from the original C++ TFHE library.
	ParamsBinaryOriginal = ParametersLiteral[uint32]{
		LWEDimension: 630,
		GLWERank:     1,
		PolyDegree:   1024,

		LWEStdDev:  0.000030517578125,
		GLWEStdDev: 0.0000000298023223876953125,

		MessageModulus: 1 << 1,

		BlindRotateParameters: GadgetParametersLiteral[uint32]{
			Base:  1 << 7,
			Level: 3,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint32]{
			Base:  1 << 2,
			Level: 8,
		},

		BootstrapOrder: OrderBlindRotateKeySwitch,
	}

	// ParamsUint2 is a parameter set with 2 bits of message space.
	ParamsUint2 = ParametersLiteral[uint64]{
		LWEDimension:    687,
		GLWERank:        3,
		PolyDegree:      512,
		LookUpTableSize: 512,

		LWEStdDev:  0.00002120846893069971872305794214,
		GLWEStdDev: 0.00000000000231841227527049948463,

		BlockSize: 3,

		MessageModulus: 1 << 2,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 18,
			Level: 1,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 4,
			Level: 3,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	// ParamsUint3 is a parameter set with 3 bits of message space.
	ParamsUint3 = ParametersLiteral[uint64]{
		LWEDimension:    820,
		GLWERank:        2,
		PolyDegree:      1024,
		LookUpTableSize: 1024,

		LWEStdDev:  0.00000251676160959795544987084234,
		GLWEStdDev: 0.00000000000000022204460492503131,

		BlockSize: 4,

		MessageModulus: 1 << 3,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 23,
			Level: 1,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 6,
			Level: 2,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	// ParamsUint4 is a parameter set with 4 bits of message space.
	ParamsUint4 = ParametersLiteral[uint64]{
		LWEDimension:    820,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048,

		LWEStdDev:  0.00000251676160959795544987084234,
		GLWEStdDev: 0.00000000000000022204460492503131,

		BlockSize: 4,

		MessageModulus: 1 << 4,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 22,
			Level: 1,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 5,
			Level: 3,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	// ParamsUint5 is a parameter set with 5 bits of message space.
	ParamsUint5 = ParametersLiteral[uint64]{
		LWEDimension:    1071,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048,

		LWEStdDev:  0.00000007088226765410429399593757,
		GLWEStdDev: 0.00000000000000022204460492503131,

		BlockSize: 7,

		MessageModulus: 1 << 5,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 22,
			Level: 1,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 6,
			Level: 3,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	// ParamsUint6 is a parameter set with 6 bits of message space.
	ParamsUint6 = ParametersLiteral[uint64]{
		LWEDimension:    1071,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 4096,

		LWEStdDev:  0.00000007088226765410429399593757,
		GLWEStdDev: 0.00000000000000022204460492503131,

		BlockSize: 7,

		MessageModulus: 1 << 6,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 22,
			Level: 1,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 6,
			Level: 3,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	// ParamsUint7 is a parameter set with 7 bits of message space.
	ParamsUint7 = ParametersLiteral[uint64]{
		LWEDimension:    1160,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 8192,

		LWEStdDev:  0.00000001966220007498402695211596,
		GLWEStdDev: 0.00000000000000022204460492503131,

		BlockSize: 8,

		MessageModulus: 1 << 7,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 22,
			Level: 1,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 7,
			Level: 3,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	/** Parameters above are NOT updated*/
	/** High precision negacyclic LUT evaluation using EBS, precision from 8 bits to 12 bits, capacity = 0.5 bits */

	// ParamsEBSTemplate is a template parameter set with 8 bits of full message space using EBS.
	//
	// for real computation, adjust the LookUpTableSize according to MessageModulus using EBSLogModulusToLUTSizeMap
	//
	// after that, use SweepParam with CapacityBits = 0.5 to find proper parameters
	ParamsEBSTemplate = ParametersLiteral[uint64]{
		LWEDimension:    1170,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048 * 8,

		LWEStdDev:  5.50160611398332e-9,
		GLWEStdDev: 7.63220286136280e-16,

		BlockSize: 1,

		MessageModulus: 1 << 8,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 22,
			Level: 1,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 7,
			Level: 3,
		},

		BootstrapOrder:          OrderKeySwitchBlindRotate,
		WorstCaseLogFailureProb: -64,

		FullTorus: true,
	}

	EBSLogModulusToLUTSizeMap = map[int]int{
		8:  2048 * 8,
		9:  2048 * 16,
		10: 2048 * 32,
		11: 2048 * 128,
		12: 2048 * 256,
	}

	/** High precision negacyclic LUT evaluation using Meta-PBS and dense keys, capacity = 0.5 bits*/

	// ParamsMetaTemplate is a template parameter set with 8 bits of full message space using Meta-FBS.
	//
	// use SweepParam with CapacityBits = 0.5 and corresonding CapacityBitsMeta to find proper parameters
	ParamsMetaTemplate = ParametersLiteral[uint64]{
		LWEDimension:    1170,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048,

		LWEStdDev:  5.50160611398332e-9,
		GLWEStdDev: 7.63220286136280e-16,

		BlockSize: 1,

		MessageModulus: 1 << 8,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 22,
			Level: 1,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 5,
			Level: 3,
		},

		BootstrapOrder:          OrderKeySwitchBlindRotate,
		WorstCaseLogFailureProb: -66,

		FullTorus:            true,
		MetaFBS:              true,
		InputNoiseIsGaussian: true,
	}
	// MetaFBSCapacityBits is an array of CapacityBits used in ParamsMetaTemplate with precision of 8-12 bits
	//
	// The results are taken from the fastest EBS-based FBS with capacity bits >= 0.5
	MetaFBSCapacityBits = map[int]float64{
		8:  3.920180,
		9:  2.808942,
		10: 1.458292,
		11: 6.114680,
		12: 3.772083,
	}
	// MetaFBSCapacityBitsMeta is an array of CapacityBitsMeta used in ParamsMetaTemplate with precision of 8-12 bits
	//
	// The corresponding RequiredExtractionRedundancy is always 1
	//
	// This guarantees that the homomorphic capacity in Meta-FBS is no lower than that in EBS
	MetaFBSCapacityBitsMeta = map[int]float64{
		8:  1.41, // cap = 5.251474
		9:  1.33, // cap = 4.243195
		10: 2.01, // cap = 1.726201
		11: 2.40, // cap = 6.384391
		12: 0.73, // cap = 3.808967
	}
	// MetaFBSCapacityBitsMeta128 is an array of CapacityBitsMeta used in ParamsMetaTemplate with precision of 8-12 bits
	//
	// The corresponding RequiredExtractionRedundancy is always 1
	//
	// This guarantees that the homomorphic capacity in Meta-FBS is no lower than that in EBS
	MetaFBSCapacityBitsMeta128 = map[int]float64{
		8:  0.32,
		9:  1.56,
		10: 2.79,
		11: 1.56,
		12: 0.60,
	}
	// ParamsUint8FullMetaFDFB is a 8-bit full-torus parameter with Meta-FBS, dense secret, gadget LUTs, and capacity for size-4 homomorphic linear combinations
	//
	// use SweepParam with one of the two argument sets
	//
	// (1) CapacityBits = ParamsUint8FullMetaFDFB.Compile().CapacityForGadgetMult(ParamsUint8FullMetaFDFB.CountLUTs-1) + math.Log2(math.Sqrt(1024)) and  CapacityBitsMeta = 3.14
	//
	// (2) CapacityBits = ParamsUint8FullMetaFDFB.Compile().CapacityForGadgetMult(ParamsUint8FullMetaFDFB.CountLUTs-1) + math.Log2(math.Sqrt(48)) and  CapacityBitsMeta = 2.68
	ParamsUint8FullMetaFDFB = ParametersLiteral[uint64]{
		LWEDimension:    970,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048,

		LWEStdDev:  1.96189341325040e-7,
		GLWEStdDev: 7.63220286136280e-16,

		BlockSize: 1,

		MessageModulus: 1 << 8,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 11,
			Level: 3,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 2,
			Level: 10,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,

		WorstCaseLogFailureProb: -42,

		FullTorus:            true,
		MetaFBS:              true,
		FullDomain:           true,
		CountLUTs:            4,
		CountCancelSignLUTs:  3,
		InputNoiseIsGaussian: true,
	}

	// ParamsLHEBase16 is a 4-bit half-torus parameter with LHE.
	//
	// No need to call SweepParam on this.
	//
	// This is only used to benchmark Refined LHE.
	//
	// Total running time of refr+extr+conv in tfhe-rs: 2*(31.397+15.338+31.291+15.079) ~= 186.21 ms (without LUT evaluation)
	//
	// var_scaled_in = 2^107.6266, var_ks = 2^111.6383, var_thres = 2^116.174
	//
	// (var_thres - var_ks) / (var_scaled_in * 8) = 44
	ParamsLHEBase16 = ParametersLiteral[uint64]{
		LWEDimension:    769,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048,

		LWEStdDev:  8.76387e-6,
		GLWEStdDev: 7.63220286136280e-16,

		BlockSize: 1,

		MessageModulus: 1 << 4,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 15,
			Level: 2,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 4,
			Level: 3,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	// ParamsLHEBase256 is a 8-bit full-torus parameter with LHE.
	//
	// No need to call SweepParam on this.
	//
	// This is only used to benchmark Refined LHE.
	//
	// Total running time of refr+extr+conv in tfhe-rs: 64.921+58.354+65.420+58.672+65.359+59.271+65.010+59.110=496.11 ms (without LUT evaluation)
	//
	// var_scaled_in = 2^102.5088, var_ks = 2^107.5798, var_thres = 2^115.338
	//
	// (var_thres - var_ks) / (var_scaled_in * 8) = 905
	ParamsLHEBase256 = ParametersLiteral[uint64]{
		LWEDimension:    953,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048,

		LWEStdDev:  3.49065e-7,
		GLWEStdDev: 7.63220286136280e-16,

		BlockSize: 1,

		MessageModulus: 1 << 8,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 9,
			Level: 4,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 7,
			Level: 2,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
	}

	ParamsTreeBased = ParametersLiteral[uint32]{
		LWEDimension:    1024,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048,

		LWEStdDev:  6.5e-8,
		GLWEStdDev: 9.6e-11,

		BlockSize: 1,

		MessageModulus: 1 << 4,

		BlindRotateParameters: GadgetParametersLiteral[uint32]{
			Base:  1 << 8,
			Level: 3,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint32]{
			Base:  1 << 10,
			Level: 2,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,

		FullTorus:                        false,
		IsDummyPublicFunctionalKeySwitch: true,
	}

	ParamsThreeBR = ParametersLiteral[uint64]{
		LWEDimension:    1170,
		GLWERank:        1,
		PolyDegree:      2048,
		LookUpTableSize: 2048,

		LWEStdDev:  5.50160611398332e-9,
		GLWEStdDev: 7.63220286136280e-16,

		BlockSize: 1,

		MessageModulus: 1 << 8,

		BlindRotateParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 16,
			Level: 4,
		},
		KeySwitchParameters: GadgetParametersLiteral[uint64]{
			Base:  1 << 9,
			Level: 2,
		},

		BootstrapOrder: OrderKeySwitchBlindRotate,
		FullTorus:      true,
	}
)

type LWEParam struct {
	Dim    int
	Stddev float64
}

// estimated using lattice-estimator 5ba00f,
// estimator.lwe.estimate(xxx, red_cost_model=estimator.reduction.RC.BDGL16 (following tfhe-rs))
// LWE dimension, stddev (modulo 1), and security level
// 770,   6.90210929630673e-6       130.11
// 870,   1.17157033549010e-6       130.10
// 970,   1.96189341325040e-7       130.17 OK
// 1070,  3.28535611423207e-8       130.14
// 1170,  5.44234288551154e-9       130.20 OK
// 1270,  9.08901969078452e-10      130.15
// 2048,  7.63220286136280e-16   	130.02 OK

// Unused...
// var LWEParamList = []LWEParam{
// 	{770, 6.90210929630673e-6},
// 	{870, 1.17157033549010e-6},
// 	{970, 1.96189341325040e-7},
// 	{1070, 3.28535611423207e-8},
// 	{1170, 5.50160611398332e-9},
// 	{1270, 9.08901969078452e-10},
// }

// func SetLWEParam[T TorusInt](paramsLit *ParametersLiteral[T], idx int) {
// 	paramsLit.LWEDimension = LWEParamList[idx].Dim
// 	paramsLit.LWEStdDev = LWEParamList[idx].Stddev
// }
