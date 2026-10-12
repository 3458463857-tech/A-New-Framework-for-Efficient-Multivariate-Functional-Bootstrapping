package tfhe

import (
	"fmt"
	"math"
	"math/bits"

	"github.com/sp301415/tfhe-go/math/poly"
	"github.com/sp301415/tfhe-go/math/vec"
)

// BootstrapFunc returns a bootstrapped LWE ciphertext with respect to given function.
func (e *Evaluator[T]) BootstrapFunc(ct LWECiphertext[T], f func(int) int) LWECiphertext[T] {
	e.GenLookUpTableAssign(f, e.buffer.lut)
	return e.BootstrapLUT(ct, e.buffer.lut)
}

// BootstrapManyFuncs returns many bootstrapped LWE ciphertexts with respect to given functions.
func (e *Evaluator[T]) BootstrapManyFuncs(ct LWECiphertext[T], funcs [](func(int) int)) []LWECiphertext[T] {
	nfuncs := len(funcs)
	if !e.Parameters.MetaFBS() {
		panic("expecting Meta-FBS")
	}
	if e.Parameters.CountLUTs() < nfuncs {
		panic("too many LUTs")
	}
	e.GenManyLookUpTablesAssign(funcs, e.buffer.lut)
	e.buffer.lut.CountLUTs = nfuncs
	return e.BootstrapManyLUTs(ct, e.buffer.lut)
}

// SgnFunc returns a function that output pfull/4 for 0 <= x < pfull/2
//
// which is the function evaluated during FDFB-CancelSign
func (e *Evaluator[T]) SgnFunc() func(int) int {
	pfull := int(e.Parameters.messageModulus)
	if !e.Parameters.fullTorus {
		pfull *= 2
	}
	// the following function extends to a sign function through negacyclicity
	return func(x int) int {
		return pfull / 4
	}
}

// GadgetDecompScalar gadget decomposes a scalar and returns the decomposed vector
func (e *Evaluator[T]) GadgetDecompScalar(scalar int, gadgetLength int) []int {
	logBases := e.buffer.gadgetScalarLogBases
	e.Parameters.GadgetFuncLogBasesAssign(gadgetLength, logBases)
	shiftBits := bits.Len(uint(e.Parameters.scale)) - 1
	vec := e.buffer.gadgetScalar[:gadgetLength]
	for i := range gadgetLength {
		logBase := logBases[i]
		val := int64(scalar) << shiftBits
		rem := (val << logBase) >> logBase
		vec[i] = int((val - rem) >> (64 - logBase))
		shiftBits += logBase
	}
	return vec
}

// GadgetFuncs generates a gadget-amplified vector of functions of the input function
func (e *Evaluator[T]) GadgetFuncs(function func(int) int, gadgetLength int) []func(int) int {
	logBases := e.buffer.gadgetScalarLogBases
	e.Parameters.GadgetFuncLogBasesAssign(gadgetLength, logBases)
	funcs := make([]func(int) int, gadgetLength)
	p := int(e.Parameters.messageModulus)
	if !e.Parameters.fullTorus {
		p *= 2
	}
	baseProd := p
	for i := range gadgetLength {
		baseProd >>= logBases[i]
		curBaseProd := baseProd
		funcs[i] = func(x int) int {
			return (function(x) * curBaseProd) % p
		}
	}
	return funcs
}

// GadgetScalarMul multiplies the multi-value entries of a Meta-PBSManyLUTs ciphertext with a scalar
func (e *Evaluator[T]) GadgetScalarMul(scalar int, ct GLWECiphertext[T], gadgetLength int) GLWECiphertext[T] {
	ctOut := NewGLWECiphertext(e.Parameters)
	e.GadgetScalarMulAssign(scalar, ct, gadgetLength, ctOut)
	return ctOut
}

// GadgetScalarMulAssign is the assigning version of GadgetScalarMul
func (e *Evaluator[T]) GadgetScalarMulAssign(scalar int, ct GLWECiphertext[T], gadgetLength int, ctOut GLWECiphertext[T]) {
	vec := e.GadgetDecompScalar(scalar, gadgetLength)
	e.ScalarMulGLWEAssign(ct, T(vec[0]), ctOut)
	ctTmp := e.buffer.ctMeta
	mvGap := e.Parameters.mvGap[e.Parameters.itersCount]
	for i := 1; i < gadgetLength; i++ {
		e.ScalarMulGLWEAssign(ct, T(vec[i]), ctTmp)
		e.MonomialMulAddGLWEAssign(ctTmp, -i*mvGap, ctOut)
	}
}

// BootstrapManyFullDomainManyFuncsRaw returns
//
// (1) an LWE ciphertext storing the sign of ct
//
// (2) a GLWE ciphertext storing the after-blind-rotation message
//
// Further constant multiplications could be done on the GLWE ciphertext before performing CancelSign
func (e *Evaluator[T]) BootstrapManyFullDomainManyFuncsRaw(ct LWECiphertext[T], funcs [](func(int) int)) (LWECiphertext[T], GLWECiphertext[T]) {
	ctSgn := NewLWECiphertextCustom[T](e.Parameters.lweDimension)
	ctGLWE := NewGLWECiphertext(e.Parameters)
	e.BootstrapManyFullDomainManyFuncsRawAssign(ct, funcs, ctSgn, ctGLWE)
	return ctSgn, ctGLWE
}

func (e *Evaluator[T]) BootstrapManyFullDomainManyFuncsRawAssign(ct LWECiphertext[T], funcs [](func(int) int), ctSgn LWECiphertext[T], ctGLWE GLWECiphertext[T]) {
	nfuncs := len(funcs)
	if !e.Parameters.MetaFBS() {
		panic("expecting Meta-FBS")
	}
	if e.Parameters.CountLUTs() < nfuncs+1 {
		panic("too many LUTs")
	}
	// the first function is the sgn function
	e.GenManyLookUpTablesAssign(append([](func(int) int){e.SgnFunc()}, funcs...), e.buffer.lut)
	e.buffer.lut.CountLUTs = nfuncs + 1
	e.BootstrapFullDomainManyLUTsAssign(ct, e.buffer.lut, ctSgn, ctGLWE)
}

// BootstrapFuncAssign bootstraps LWE ciphertext with respect to given function and writes it to ctOut.
func (e *Evaluator[T]) BootstrapFuncAssign(ct LWECiphertext[T], f func(int) int, ctOut LWECiphertext[T]) {
	e.GenLookUpTableAssign(f, e.buffer.lut)
	e.BootstrapLUTAssign(ct, e.buffer.lut, ctOut)
}

// BootstrapLUT returns a bootstrapped LWE ciphertext with respect to given LUT.
func (e *Evaluator[T]) BootstrapLUT(ct LWECiphertext[T], lut LookUpTable[T]) LWECiphertext[T] {
	ctOut := NewLWECiphertext(e.Parameters)
	e.BootstrapLUTAssign(ct, lut, ctOut)
	return ctOut
}

// BootstrapManyLUTs returns a list bootstrapped LWE ciphertexts with respect to given LUT.
func (e *Evaluator[T]) BootstrapManyLUTs(ct LWECiphertext[T], lut LookUpTable[T]) []LWECiphertext[T] {
	ctOut := make([]LWECiphertext[T], lut.CountLUTs)
	for i := range ctOut {
		ctOut[i] = NewLWECiphertext(e.Parameters)
	}
	e.BootstrapManyLUTsAssign(ct, lut, ctOut)
	return ctOut
}

// BootstrapLUTAssign bootstraps LWE ciphertext with respect to given LUT and writes it to ctOut.
func (e *Evaluator[T]) BootstrapLUTAssign(ct LWECiphertext[T], lut LookUpTable[T], ctOut LWECiphertext[T]) {
	switch e.Parameters.bootstrapOrder {
	case OrderKeySwitchBlindRotate:
		e.KeySwitchForBootstrapAssign(ct, e.buffer.ctKeySwitchForBootstrap)
		e.MetaFBSAssign(e.buffer.ctKeySwitchForBootstrap, lut, e.buffer.ctRotate)
		// e.BlindRotateAssign(e.buffer.ctKeySwitchForBootstrap, lut, e.buffer.ctRotate)
		e.buffer.ctRotate.ToLWECiphertextAssign(0, ctOut)
	case OrderBlindRotateKeySwitch:
		e.MetaFBSAssign(ct, lut, e.buffer.ctRotate)
		// e.BlindRotateAssign(ct, lut, e.buffer.ctRotate)
		e.buffer.ctRotate.ToLWECiphertextAssign(0, e.buffer.ctExtract)
		e.KeySwitchForBootstrapAssign(e.buffer.ctExtract, ctOut)
	}
}

// BootstrapManyLUTsAssign bootstraps LWE ciphertext with respect to given multi-value LUT and writes it to ctOut.
func (e *Evaluator[T]) BootstrapManyLUTsAssign(ct LWECiphertext[T], lut LookUpTable[T], ctOut []LWECiphertext[T]) {
	switch e.Parameters.bootstrapOrder {
	case OrderKeySwitchBlindRotate:
		e.KeySwitchForBootstrapAssign(ct, e.buffer.ctKeySwitchForBootstrap)
		e.MetaFBSAssign(e.buffer.ctKeySwitchForBootstrap, lut, e.buffer.ctRotate)
		// e.BlindRotateAssign(e.buffer.ctKeySwitchForBootstrap, lut, e.buffer.ctRotate)
		gap := e.Parameters.mvGap[e.Parameters.itersCount]
		for i := range lut.CountLUTs {
			e.buffer.ctRotate.ToLWECiphertextAssign(i*gap, ctOut[i])
		}
	case OrderBlindRotateKeySwitch:
		e.MetaFBSAssign(ct, lut, e.buffer.ctRotate)
		// e.BlindRotateAssign(ct, lut, e.buffer.ctRotate)
		gap := e.Parameters.mvGap[e.Parameters.itersCount]
		for i := range lut.CountLUTs {
			e.buffer.ctRotate.ToLWECiphertextAssign(i*gap, e.buffer.ctExtract)
			e.KeySwitchForBootstrapAssign(e.buffer.ctExtract, ctOut[i])
		}
	}
}

// BootstrapFullDomainManyLUTsAssign bootstraps LWE ciphertext with respect to given multi-value full-domain LUT,
// writing the LWE ciphertext storing the sign of ct to ctSgn, writing the blind-rotated GLWE ciphertext ctGLWE
func (e *Evaluator[T]) BootstrapFullDomainManyLUTsAssign(ct LWECiphertext[T], lut LookUpTable[T], ctSgn LWECiphertext[T], ctGLWE GLWECiphertext[T]) {
	switch e.Parameters.bootstrapOrder {
	case OrderKeySwitchBlindRotate:
		e.KeySwitchForBootstrapAssign(ct, e.buffer.ctKeySwitchForBootstrap)
		e.MetaFBSAssign(e.buffer.ctKeySwitchForBootstrap, lut, e.buffer.ctRotate)
		// e.debugGLWE("After Meta-FBS", e.buffer.ctRotate)
		ctGLWE.CopyFrom(e.buffer.ctRotate)

		e.buffer.ctRotate.ToLWECiphertextAssign(0, e.buffer.ctExtract)
		e.KeySwitchForBootstrapAssign(e.buffer.ctExtract, e.buffer.ctKeySwitchForBootstrap)
		ctSgnModulus := 2 * e.Parameters.polyDegree
		ctQuo, _, _ := e.ApproximateEuclideanDivision(e.buffer.ctKeySwitchForBootstrap, e.Parameters.blindRotateParameters.sizeT, ctSgnModulus)
		ctQuo.Value[0] -= T(ctSgnModulus / 4)
		ctSgn.CopyFrom(ctQuo)
		// debugf("Phase(ctSgn) = %d\n", e.Encryptor.DecryptLWEPhase(ctQuo).Value%T(ctSgnModulus))
	case OrderBlindRotateKeySwitch:
		panic("Not supported")
	}
}

// CancelSign is used in a Meta-FDFB to remove the sign bit in the message underlying ctGLWE
// it outputs the subLUT values in range [start, end), with 1 <= start < end <= countLUTs
func (e *Evaluator[T]) CancelSign(ctSgn LWECiphertext[T], ctGLWE GLWECiphertext[T], start int, end int) []LWECiphertext[T] {
	countLUTs := e.Parameters.countLUTs
	start = max(min(start, countLUTs), 1)
	end = max(min(end, countLUTs), 1, start)
	ctOut := make([]LWECiphertext[T], end-start)
	for i := range ctOut {
		ctOut[i] = NewLWECiphertext(e.Parameters)
	}
	e.CancelSignAssign(ctSgn, ctGLWE, ctOut, start, end)
	return ctOut
}

// CancelSignAssign is the assigning version of CancelSign
func (e *Evaluator[T]) CancelSignAssign(ctSgn LWECiphertext[T], ctGLWE GLWECiphertext[T], ctOut []LWECiphertext[T], start int, end int) {
	gap := e.Parameters.mvGap[e.Parameters.itersCount]
	countCancelSignLUTs := e.Parameters.countCancelSignLUTs
	bufRotate, bufTr, bufSum := e.buffer.glweFDFB[0],
		e.buffer.glweFDFB[1], e.buffer.glweFDFB[2]
	bufRotate.CopyFrom(ctGLWE)
	curLUTcount := 0
	packingDistance := e.Parameters.polyDegree / e.Parameters.countCancelSignLUTs
	for j := range bufRotate.Value {
		vec.RotateInPlaceNegacyclic(bufRotate.Value[j].Coeffs, -gap*(start-1))
	}
	for i := start; i < end; i++ {
		for j := range bufRotate.Value {
			vec.RotateInPlaceNegacyclic(bufRotate.Value[j].Coeffs, -gap)
		}
		e.TruncRepeat(bufRotate, e.Parameters.itersCount, bufTr)
		e.debugGLWE("After Tr for CancelSign", bufTr)
		if curLUTcount == 0 {
			bufSum.CopyFrom(bufTr)
		} else {
			for j := range bufRotate.Value {
				vec.RotateInPlaceNegacyclic(bufTr.Value[j].Coeffs, curLUTcount*packingDistance)
			}
			e.AddGLWEAssign(bufSum, bufTr, bufSum)
		}
		curLUTcount++
		if curLUTcount >= countCancelSignLUTs {
			e.debugGLWE("Before CancelSign", bufSum)
			e.BlindRotateCiphertextAssign(ctSgn, bufSum, bufTr)
			e.debugGLWE("After CancelSign", bufTr)
			for j := range countCancelSignLUTs {
				bufTr.ToLWECiphertextAssign(j*packingDistance, ctOut[i-start+j-countCancelSignLUTs+1])
			}
			curLUTcount = 0
		}
	}
	if curLUTcount > 0 {
		e.BlindRotateCiphertextAssign(ctSgn, bufSum, bufTr)
		for j := range curLUTcount {
			bufTr.ToLWECiphertextAssign(j*packingDistance, ctOut[j+end-start-curLUTcount])
		}
	}
}

// ApproximateEuclideanDivision performs approximate homomorphic Euclidean division on ct,
//
// ct should have a ciphertext modulus of Q and be balance-reduced modulo Q
//
// The quotient and remainder ciphertexts w.r.t. divRem by Q/base on ct are returned
//
// To avoid modular redution by integers, Q/base is scaled to the largest power of two <= 2^64/base
//
// # This scaling introduces a negligible error to the ciphertext
//
// The remainder is balance-reduced modulo this new modulus, and the bit length of the modulus is returned
func (e *Evaluator[T]) ApproximateEuclideanDivision(ct LWECiphertext[T], logQ int, base int) (LWECiphertext[T], LWECiphertext[T], int) {
	if float64(logQ) < math.Log2(float64(base)) {
		panic("repeatBase larger than current ciphertext modulus")
	}
	ctQuo := e.buffer.ctQuo
	ctRem := e.buffer.ctRem
	if float64(logQ) == math.Log2(float64(base)) {
		ctQuo.CopyFrom(ct)
		ctRem.Clear()
		return ctQuo, ctRem, 0
	}

	if e.Parameters.blindRotateParameters.sizeT != 64 {
		panic("expecting 64 bits of T")
	}

	ctQuo.CopyFrom(ct)
	logDelta := 0
	if (base & (base - 1)) != 0 {
		// scale Q/base to maximum power-of-two <= 2^64 / base
		logDelta = bits.Len(PrevPowerOfTwo(uint(math.Pow(2, 64)/float64(base)))) - 1
		scalingFactor := math.Pow(2, -float64(logQ)) * float64(base) * math.Pow(2, float64(logDelta))
		for i := range ct.Value {
			ctQuo.Value[i] = T(math.Round(float64(int64(ctQuo.Value[i])) * scalingFactor))
		}
	} else {
		logDelta = logQ - int(math.Log2(float64(base)))
	}
	maskDelta := (T(1) << logDelta) - 1
	var src T
	for i := range len(ct.Value) {
		src = ctQuo.Value[i]
		ctRem.Value[i] = T((int64(src&maskDelta) << (64 - logDelta)) >> (64 - logDelta))
		ctQuo.Value[i] = T(int64(src-ctRem.Value[i]) >> logDelta)
	}
	return ctQuo, ctRem, logDelta
}

// TruncRepeat performs the following operation:
//
// 1. It truncates the encrypted Laurent polynomial to degree [-truncBound, truncBound], resulting in m0(X)
//
// 2. It performs X->X^repeatBase on m0(X) to obtain m1(X) = m0(X^repeatBase)
//
// 3. It fills the coefficients in m1(X) corresponding to X^(i*repeatBase*k) with m0[i] for -repeatBase/2 <= k < repeatBase/2
//
// Note: coeffcients unaffected by step 3 may contain garbage values (when extendedCoeffsCount > 0)
//
// The noise growth is additive, and the number of plaintext-RLev products is ceil(N/(extendedCoeffsCount+1))
//
// TruncRepeat is used as a subroutine between blind rotations in Meta-FBS and in LWE-to-RLWE packing in Meta-FDFB
func (e *Evaluator[T]) TruncRepeat(ct GLWECiphertext[T], curIter int, ctOut GLWECiphertext[T]) {
	p := e.Parameters
	var truncBound int
	repeatBase := p.repeatBase[curIter]
	extendedCoeffsCount := p.extendedCoeffsCount[curIter]
	N := p.polyDegree
	trk := e.EvaluationKey.TruncationKey[curIter]

	if p.glweRank != 1 {
		panic("expecting RLWE ciphertexts")
	}

	ctOut.Clear()

	trForFDFB := (p.itersCount == curIter)

	var truncBoundHigh int
	var redundancy int

	truncBound = p.truncationBound[curIter]
	truncBoundHigh = truncBound + (p.countLUTs-1)*p.mvGap[curIter]
	if trForFDFB {
		truncBoundHigh = truncBound
	}
	redundancy = p.redundancy[curIter]
	// b is unaffected by extendedCoeffsCount
	// the repetition polynomial, (1+...+X^{repeatBase-1})*X^{-some offset},
	//  needs to be incorporated into trunc(b)[X^repeatBase]
	for i := 0; i <= truncBoundHigh; i++ {
		for j := i * repeatBase; j < (i+1)*repeatBase; j++ {
			ctOut.Value[0].Coeffs[j] = ct.Value[0].Coeffs[i]
		}
	}
	for i := 1; i <= truncBound; i++ {
		for j := N - i*repeatBase; j < N-(i-1)*repeatBase; j++ {
			ctOut.Value[0].Coeffs[j] = ct.Value[0].Coeffs[N-i]
		}
	}

	// XXX: debug
	// ad hoc fix
	// expecting ctOut equals ctOut * X^mask[i] during iter i
	// mask := make([]T, len(trk.Value))
	// e.Encryptor.UniformSampler.SampleVecAssign(mask)

	// a is split into len(trk.Value) = ceil(polydegree / (extendedCoeffsCount + 1)) fragments
	// the repetition polynomial is included in the truncation keys (or neglected in Meta-FDFB)
	for i := range trk.Value {
		// XXX: debug
		// rotLen := int(mask[i])
		// if i > 0 {
		// 	rotLen -= int(mask[i-1])
		// }
		// for j := range 2 {
		// 	vec.RotateInPlaceNegacyclic(ctOut.Value[j].Coeffs, rotLen)
		// }

		// [colStart, colEnd) in the LWE negacyclic matrix
		colStart := i * (extendedCoeffsCount + 1)
		colEnd := min(colStart+extendedCoeffsCount+1, N)
		colCount := colEnd - colStart
		// truncate m0*X^colStart to degree [-truncBound-(colCout-1), truncBound]
		buffPoly1, buffPoly2 := e.buffer.polyTruncRepeat[0], e.buffer.polyTruncRepeat[1]
		copy(buffPoly1.Coeffs, ct.Value[1].Coeffs)
		vec.RotateInPlaceNegacyclic(buffPoly1.Coeffs, colStart)

		buffPoly2.Clear()
		for j := 0; j <= truncBoundHigh; j++ {
			buffPoly2.Coeffs[j*repeatBase] = buffPoly1.Coeffs[j]
		}
		for j := 1; j <= truncBound+colCount-1; j++ {
			buffPoly2.Coeffs[N-j*repeatBase] = buffPoly1.Coeffs[N-j]
		}
		// XXX: debug
		// vec.RotateInPlaceNegacyclic(buffPoly2.Coeffs, int(mask[i]))
		// XXX: we can add all the gadget products in FFT domain and use one iFFT in the end,
		//  but this may harm the precision, so we do not use this for now
		e.GadgetProductAddGLWEAssign(trk.Value[i], buffPoly2, ctOut)
	}
	// XXX: debug
	// for j := range 2 {
	// 	vec.RotateInPlaceNegacyclic(ctOut.Value[j].Coeffs, -int(mask[len(mask)-1]))
	// }

	// suppose truncRepeat outputs TV' * X^(err),
	//  we want to center the redundant entries of the constant block (countLUTs lowest blocks) of TV'
	prevOffset := redundancy / 2
	targetOffset := (redundancy * repeatBase) / 2
	diffOffset := targetOffset - prevOffset*repeatBase
	for i := range ctOut.Value {
		vec.RotateInPlaceNegacyclic(ctOut.Value[i].Coeffs, -diffOffset)
	}
}

var debugFlag bool = false

func SetDebug(flag bool) {
	debugFlag = flag
}

func debugf(format string, a ...any) {
	if debugFlag {
		fmt.Printf(format, a...)
	}
}

func debugln(a ...any) {
	if debugFlag {
		fmt.Println(a...)
	}
}

func (e *Evaluator[T]) debugGLWE(info string, ct GLWECiphertext[T]) {
	if debugFlag {
		phase := e.Encryptor.DecryptGLWEPhase(ct)
		clear := e.DecodeGLWE(phase)
		debugln(info)
		debugln(clear)
		debugln()
	}
}

func (e *Evaluator[T]) MetaFBSAssign(ct LWECiphertext[T], lut LookUpTable[T], ctOut GLWECiphertext[T]) {
	if e.Parameters.metaFBS {
		// 1. prepare LUT (just use the input)
		// 2. Euclidean division by 2N with remainder
		firstModulus := 2 * e.Parameters.polyDegree
		if e.Parameters.fullDomain {
			firstModulus /= 2
		}
		ctQuo, ctRem, curLogQ := e.ApproximateEuclideanDivision(ct, e.Parameters.blindRotateParameters.sizeT,
			firstModulus)
		// debugf("phase(ct) = %d, quo = %d, rem = %d\n",
		// 	int(e.Encryptor.DecryptLWEPhase(ct).Value),
		// 	int(e.Encryptor.DecryptLWEPhase(ctQuo).Value)%(2*e.Parameters.polyDegree),
		// 	int(e.Encryptor.DecryptLWEPhase(ctRem).Value))
		// 3. blind rotate LUT by signed integers (quotient in 2)
		ctTmp := e.buffer.ctMeta
		e.BlindRotateAssign(ctQuo, lut, ctOut)
		// e.debugGLWE("After first bts", ctOut)
		// >begin loop
		for i := range e.Parameters.itersCount {
			// >4. Euclidean division with remainder
			ctQuo, ctRem, curLogQ = e.ApproximateEuclideanDivision(ctRem, curLogQ, e.Parameters.repeatBase[i])
			// XXX: debug, sample unbiased ctQuo
			// {
			// 	e.Encryptor.UniformSampler.SampleVecAssign(ctQuo.Value)
			// 	for j := range e.Parameters.lweDimension + 1 {
			// 		// U([-2, 2])
			// 		for (ctQuo.Value[j] % 8) >= 5 {
			// 			ctQuo.Value[j] = e.Encryptor.UniformSampler.Sample()
			// 		}
			// 		ctQuo.Value[j] %= 8
			// 		ctQuo.Value[j] -= 2
			// 	}
			// }
			// debugf("phase(%d-th quo) = %d\n", i, int(e.Encryptor.DecryptLWEPhase(ctQuo).Value))
			// debugf("%d-th div, quo = %d, rem = %d\n",
			// 	i,
			// 	int(e.Encryptor.DecryptLWEPhase(ctQuo).Value),
			// 	int(e.Encryptor.DecryptLWEPhase(ctRem).Value))
			// >5. truncated repetition
			e.TruncRepeat(ctOut, i, ctTmp)
			// XXX: debug, skip TruncRepeat
			// ctTmp.CopyFrom(ctOut)
			// e.debugGLWE(fmt.Sprintf("After %d-th tr", i), ctTmp)
			// >6. blind rotate ciphertext by signed integers (quotient in 4)
			e.BlindRotateCiphertextAssign(ctQuo, ctTmp, ctOut)
			// e.debugGLWE(fmt.Sprintf("After %d-th bts", i), ctOut)
			// 7. exit on last iter, otherwise goto 4
		}
		// >end loop
	} else {
		e.BlindRotateAssign(ct, lut, ctOut)
	}
}

// ModSwitch switches the modulus of x from Q to 2 * LookUpTableSize in a non Meta-FBS
//
// Important: in Meta-FBS, ModSwitch(x) simply returns the signed form of x (assuming x has been bit-extended corrrectly)
func (e *Evaluator[T]) ModSwitch(x T) int {
	if e.Parameters.metaFBS {
		return int(x)
	} else {
		return int(math.Round(e.modSwitchConstant*float64(x))) % (2 * e.Parameters.lookUpTableSize)
	}
}

// BlindRotate returns the blind rotation of LWE ciphertext with respect to LUT.
func (e *Evaluator[T]) BlindRotate(ct LWECiphertext[T], lut LookUpTable[T]) GLWECiphertext[T] {
	ctOut := NewGLWECiphertext(e.Parameters)
	e.BlindRotateAssign(ct, lut, ctOut)
	return ctOut
}

// BlindRotateAssign computes the blind rotation of LWE ciphertext with respect to LUT, and writes it to ctOut.
func (e *Evaluator[T]) BlindRotateAssign(ct LWECiphertext[T], lut LookUpTable[T], ctOut GLWECiphertext[T]) {
	switch {
	case e.Parameters.lookUpTableSize > e.Parameters.polyDegree:
		e.blindRotateExtendedAssign(ct, lut, ctOut)
	case e.Parameters.blockSize > 1:
		e.blindRotateBlockAssign(ct, lut, ctOut)
	default:
		e.blindRotateOriginalAssign(ct, lut, ctOut)
	}
}

// BlindRotateAssign computes the blind rotation of LWE ciphertext with respect to LUT, and writes it to ctOut.
func (e *Evaluator[T]) BlindRotateCiphertextAssign(ct LWECiphertext[T], ctIn GLWECiphertext[T], ctOut GLWECiphertext[T]) {
	switch {
	case e.Parameters.lookUpTableSize > e.Parameters.polyDegree:
		e.blindRotateCiphertextExtendedAssign(ct, ctIn, ctOut)
	case e.Parameters.blockSize > 1:
		e.blindRotateCiphertextBlockAssign(ct, ctIn, ctOut)
	default:
		e.blindRotateCiphertextOriginalAssign(ct, ctIn, ctOut)
	}
}

// blindRotateExtendedAssign computes the blind rotation when LookUpTableSize > PolyDegree.
// This is equivalent to the blind rotation algorithm using extended polynomials, as explained in https://eprint.iacr.org/2023/402.
func (e *Evaluator[T]) blindRotateExtendedAssign(ct LWECiphertext[T], lut LookUpTable[T], ctOut GLWECiphertext[T]) {
	polyDecomposed := e.Decomposer.buffer.polyDecomposed[:e.Parameters.blindRotateParameters.level]

	b2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[0])
	b2NMono, b2NIdx := b2N/e.Parameters.polyExtendFactor, b2N%e.Parameters.polyExtendFactor

	for i, ii := 0, e.Parameters.polyExtendFactor-b2NIdx; i < b2NIdx; i, ii = i+1, ii+1 {
		e.PolyEvaluator.MonomialMulPolyAssign(lut.Value[i], b2NMono+1, e.buffer.ctAcc[ii].Value[0])
	}
	for i, ii := b2NIdx, 0; i < e.Parameters.polyExtendFactor; i, ii = i+1, ii+1 {
		e.PolyEvaluator.MonomialMulPolyAssign(lut.Value[i], b2NMono, e.buffer.ctAcc[ii].Value[0])
	}

	for i := 0; i < e.Parameters.polyExtendFactor; i++ {
		for j := 1; j < e.Parameters.glweRank+1; j++ {
			e.buffer.ctAcc[i].Value[j].Clear()
		}
	}

	for j := 0; j < e.Parameters.polyExtendFactor; j++ {
		e.Decomposer.DecomposePolyAssign(e.buffer.ctAcc[j].Value[0], e.Parameters.blindRotateParameters, polyDecomposed)
		for l := 0; l < e.Parameters.blindRotateParameters.level; l++ {
			e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[l], e.buffer.ctAccFourierDecomposed[j][0][l])
		}
	}

	a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[1])
	a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

	for k := 0; k < e.Parameters.polyExtendFactor; k++ {
		e.GadgetProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[0].Value[0], e.buffer.ctAccFourierDecomposed[k][0], e.buffer.ctBlockFourierAcc[k])
	}

	if a2NIdx == 0 {
		e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
		for k := 0; k < e.Parameters.polyExtendFactor; k++ {
			e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[k], e.buffer.fMono, e.buffer.ctFourierAcc[k])
		}
	} else {
		e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
		for k, kk := 0, e.Parameters.polyExtendFactor-a2NIdx; k < a2NIdx; k, kk = k+1, kk+1 {
			e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
			e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
		}
		e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono, e.buffer.fMono)
		for k, kk := a2NIdx, 0; k < e.Parameters.polyExtendFactor; k, kk = k+1, kk+1 {
			e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
			e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
		}
	}

	for j := 1; j < e.Parameters.blockSize; j++ {
		a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[j+1])
		a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

		for k := 0; k < e.Parameters.polyExtendFactor; k++ {
			e.GadgetProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j].Value[0], e.buffer.ctAccFourierDecomposed[k][0], e.buffer.ctBlockFourierAcc[k])
		}

		if a2NIdx == 0 {
			e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
			for k := 0; k < e.Parameters.polyExtendFactor; k++ {
				e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[k], e.buffer.fMono, e.buffer.ctFourierAcc[k])
			}
		} else {
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
			for k, kk := 0, e.Parameters.polyExtendFactor-a2NIdx; k < a2NIdx; k, kk = k+1, kk+1 {
				e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
			}
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono, e.buffer.fMono)
			for k, kk := a2NIdx, 0; k < e.Parameters.polyExtendFactor; k, kk = k+1, kk+1 {
				e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
			}
		}
	}

	for j := 0; j < e.Parameters.polyExtendFactor; j++ {
		for k := 0; k < e.Parameters.glweRank+1; k++ {
			e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[j].Value[k], e.buffer.ctAcc[j].Value[k])
		}
	}

	for i := 1; i < e.Parameters.blockCount-1; i++ {
		for j := 0; j < e.Parameters.polyExtendFactor; j++ {
			for k := 0; k < e.Parameters.glweRank+1; k++ {
				e.Decomposer.DecomposePolyAssign(e.buffer.ctAcc[j].Value[k], e.Parameters.blindRotateParameters, polyDecomposed)
				for l := 0; l < e.Parameters.blindRotateParameters.level; l++ {
					e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[l], e.buffer.ctAccFourierDecomposed[j][k][l])
				}
			}
		}

		a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[i*e.Parameters.blockSize+1])
		a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

		for k := 0; k < e.Parameters.polyExtendFactor; k++ {
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[i*e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[k], e.buffer.ctBlockFourierAcc[k])
		}

		if a2NIdx == 0 {
			e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
			for k := 0; k < e.Parameters.polyExtendFactor; k++ {
				e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[k], e.buffer.fMono, e.buffer.ctFourierAcc[k])
			}
		} else {
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
			for k, kk := 0, e.Parameters.polyExtendFactor-a2NIdx; k < a2NIdx; k, kk = k+1, kk+1 {
				e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
			}
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono, e.buffer.fMono)
			for k, kk := a2NIdx, 0; k < e.Parameters.polyExtendFactor; k, kk = k+1, kk+1 {
				e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
			}
		}

		for j := i*e.Parameters.blockSize + 1; j < (i+1)*e.Parameters.blockSize; j++ {
			a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[j+1])
			a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

			for k := 0; k < e.Parameters.polyExtendFactor; k++ {
				e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[k], e.buffer.ctBlockFourierAcc[k])
			}

			if a2NIdx == 0 {
				e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
				for k := 0; k < e.Parameters.polyExtendFactor; k++ {
					e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[k], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				}
			} else {
				e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
				for k, kk := 0, e.Parameters.polyExtendFactor-a2NIdx; k < a2NIdx; k, kk = k+1, kk+1 {
					e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
					e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
				}
				e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono, e.buffer.fMono)
				for k, kk := a2NIdx, 0; k < e.Parameters.polyExtendFactor; k, kk = k+1, kk+1 {
					e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
					e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
				}
			}
		}

		for j := 0; j < e.Parameters.polyExtendFactor; j++ {
			for k := 0; k < e.Parameters.glweRank+1; k++ {
				e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[j].Value[k], e.buffer.ctAcc[j].Value[k])
			}
		}
	}

	for j := 0; j < e.Parameters.polyExtendFactor; j++ {
		for k := 0; k < e.Parameters.glweRank+1; k++ {
			e.Decomposer.DecomposePolyAssign(e.buffer.ctAcc[j].Value[k], e.Parameters.blindRotateParameters, polyDecomposed)
			for l := 0; l < e.Parameters.blindRotateParameters.level; l++ {
				e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[l], e.buffer.ctAccFourierDecomposed[j][k][l])
			}
		}
	}

	a2N = 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[e.Parameters.lweDimension-e.Parameters.blockSize+1])
	a2NMono, a2NIdx = a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

	if a2NIdx == 0 {
		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[e.Parameters.lweDimension-e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
		e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
		e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
	} else {
		kk := e.Parameters.polyExtendFactor - a2NIdx
		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[e.Parameters.lweDimension-e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[e.Parameters.lweDimension-e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[kk], e.buffer.ctBlockFourierAcc[kk])
		e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
		e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[0])
		e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[0], e.buffer.ctBlockFourierAcc[0], e.buffer.ctFourierAcc[0])
	}

	for j := e.Parameters.lweDimension - e.Parameters.blockSize + 1; j < e.Parameters.lweDimension; j++ {
		a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[j+1])
		a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

		if a2NIdx == 0 {
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
			e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
			e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
		} else {
			kk := e.Parameters.polyExtendFactor - a2NIdx
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[kk], e.buffer.ctBlockFourierAcc[kk])
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
			e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[0])
			e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[0], e.buffer.ctBlockFourierAcc[0], e.buffer.ctFourierAcc[0])
		}
	}

	for k := 0; k < e.Parameters.glweRank+1; k++ {
		e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[0].Value[k], e.buffer.ctAcc[0].Value[k])
		ctOut.Value[k].CopyFrom(e.buffer.ctAcc[0].Value[k])
	}
}

// blindRotateBlockAssign computes the blind rotation when PolyDegree = LookUpTableSize and BlockSize > 1.
// This is equivalent to the blind rotation algorithm using block binary keys, as explained in https://eprint.iacr.org/2023/958.
func (e *Evaluator[T]) blindRotateBlockAssign(ct LWECiphertext[T], lut LookUpTable[T], ctOut GLWECiphertext[T]) {
	polyDecomposed := e.Decomposer.buffer.polyDecomposed[:e.Parameters.blindRotateParameters.level]

	e.PolyEvaluator.MonomialMulPolyAssign(lut.Value[0], -e.ModSwitch(ct.Value[0]), ctOut.Value[0])
	for i := 1; i < e.Parameters.glweRank+1; i++ {
		ctOut.Value[i].Clear()
	}

	e.Decomposer.DecomposePolyAssign(ctOut.Value[0], e.Parameters.blindRotateParameters, polyDecomposed)
	for k := 0; k < e.Parameters.blindRotateParameters.level; k++ {
		e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[k], e.buffer.ctAccFourierDecomposed[0][0][k])
	}

	e.GadgetProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[0].Value[0], e.buffer.ctAccFourierDecomposed[0][0], e.buffer.ctBlockFourierAcc[0])
	e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[1]), e.buffer.fMono)
	e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
	for j := 1; j < e.Parameters.blockSize; j++ {
		e.GadgetProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j].Value[0], e.buffer.ctAccFourierDecomposed[0][0], e.buffer.ctBlockFourierAcc[0])
		e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[j+1]), e.buffer.fMono)
		e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
	}

	for j := 0; j < e.Parameters.glweRank+1; j++ {
		e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[0].Value[j], ctOut.Value[j])
	}

	for i := 1; i < e.Parameters.blockCount; i++ {
		for j := 0; j < e.Parameters.glweRank+1; j++ {
			e.Decomposer.DecomposePolyAssign(ctOut.Value[j], e.Parameters.blindRotateParameters, polyDecomposed)
			for k := 0; k < e.Parameters.blindRotateParameters.level; k++ {
				e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[k], e.buffer.ctAccFourierDecomposed[0][j][k])
			}
		}

		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[i*e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
		e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[i*e.Parameters.blockSize+1]), e.buffer.fMono)
		e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
		for j := i*e.Parameters.blockSize + 1; j < (i+1)*e.Parameters.blockSize; j++ {
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
			e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[j+1]), e.buffer.fMono)
			e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
		}

		for j := 0; j < e.Parameters.glweRank+1; j++ {
			e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[0].Value[j], ctOut.Value[j])
		}
	}
}

// blindRotateOriginalAssign computes the blind rotation when PolyDegree = LookUpTableSize and BlockSize = 1.
// This is equivalent to the original blind rotation algorithm.
func (e *Evaluator[T]) blindRotateOriginalAssign(ct LWECiphertext[T], lut LookUpTable[T], ctOut GLWECiphertext[T]) {
	polyDecomposed := e.Decomposer.buffer.polyDecomposed[:e.Parameters.blindRotateParameters.level]

	e.PolyEvaluator.MonomialMulPolyAssign(lut.Value[0], -e.ModSwitch(ct.Value[0]), ctOut.Value[0])
	for i := 1; i < e.Parameters.glweRank+1; i++ {
		ctOut.Value[i].Clear()
	}

	// XXX: randomized blind rotation
	var rotMask []T = nil
	if e.Parameters.RandomizedBlindRotate {
		rotMask = make([]T, e.Parameters.lweDimension)
		e.Encryptor.UniformSampler.SampleVecAssign(rotMask)
		rotMask[e.Parameters.lweDimension-1] = 0
		for i := 0; i < e.Parameters.lweDimension-1; i++ {
			rotMask[e.Parameters.lweDimension-1] -= rotMask[i]
		}
		for j, mask := 0, int(rotMask[0]); j < e.Parameters.glweRank+1; j++ {
			e.PolyEvaluator.MonomialMulPolyInPlace(ctOut.Value[j], mask)
		}
	}

	e.PolyEvaluator.MonomialMulPolyAssign(ctOut.Value[0], -e.ModSwitch(ct.Value[1]), e.buffer.mono)
	e.PolyEvaluator.SubPolyAssign(e.buffer.mono, ctOut.Value[0], e.buffer.mono)
	e.Decomposer.DecomposePolyAssign(e.buffer.mono, e.Parameters.blindRotateParameters, polyDecomposed)
	for k := 0; k < e.Parameters.blindRotateParameters.level; k++ {
		e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[k], e.buffer.ctAccFourierDecomposed[0][0][k])
	}

	e.GadgetProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[0].Value[0], e.buffer.ctAccFourierDecomposed[0][0], e.buffer.ctFourierAcc[0])
	// e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[1]), e.buffer.fMono)
	// e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
	for j := 0; j < e.Parameters.glweRank+1; j++ {
		e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[0].Value[j], ctOut.Value[j])
	}

	for i := 1; i < e.Parameters.lweDimension; i++ {
		// XXX: randomized blind rotation
		if e.Parameters.RandomizedBlindRotate {
			for j, mask := 0, int(rotMask[i]); j < e.Parameters.glweRank+1; j++ {
				e.PolyEvaluator.MonomialMulPolyInPlace(ctOut.Value[j], mask)
			}
		}
		// fixed original blind rotation
		//  implemented: (X^-ai-1) * <Decomp(ACC), GGSW> + ACC
		//  should be: <Decomp(ACC*(X^-ai-1)), GGSW> + ACC to reduce noise variance by 2?
		exponent := -e.ModSwitch(ct.Value[i+1])
		for j := 0; j < e.Parameters.glweRank+1; j++ {
			e.PolyEvaluator.MonomialMulPolyAssign(ctOut.Value[j], exponent, e.buffer.mono)
			e.PolyEvaluator.SubPolyAssign(e.buffer.mono, ctOut.Value[j], e.buffer.mono)
			e.Decomposer.DecomposePolyAssign(e.buffer.mono, e.Parameters.blindRotateParameters, polyDecomposed)
			for k := 0; k < e.Parameters.blindRotateParameters.level; k++ {
				e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[k], e.buffer.ctAccFourierDecomposed[0][j][k])
			}
		}
		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[i], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctFourierAcc[0])
		// e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[i+1]), e.buffer.fMono)
		// e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])

		for j := 0; j < e.Parameters.glweRank+1; j++ {
			e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[0].Value[j], ctOut.Value[j])
		}
	}
}

// blindRotateCiphertextExtendedAssign computes the ciphertext blind rotation when LookUpTableSize > PolyDegree.
// This is equivalent to the blind rotation algorithm using extended polynomials, as explained in https://eprint.iacr.org/2023/402.
// TODO: EBS
func (e *Evaluator[T]) blindRotateCiphertextExtendedAssign(ct LWECiphertext[T], ctIn GLWECiphertext[T], ctOut GLWECiphertext[T]) {
	polyDecomposed := e.Decomposer.buffer.polyDecomposed[:e.Parameters.blindRotateParameters.level]
	// b2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[0])
	// b2NMono, b2NIdx := b2N/e.Parameters.polyExtendFactor, b2N%e.Parameters.polyExtendFactor

	// for i, ii := 0, e.Parameters.polyExtendFactor-b2NIdx; i < b2NIdx; i, ii = i+1, ii+1 {
	// 	e.PolyEvaluator.MonomialMulPolyAssign(lut.Value[i], b2NMono+1, e.buffer.ctAcc[ii].Value[0])
	// }
	// for i, ii := b2NIdx, 0; i < e.Parameters.polyExtendFactor; i, ii = i+1, ii+1 {
	// 	e.PolyEvaluator.MonomialMulPolyAssign(lut.Value[i], b2NMono, e.buffer.ctAcc[ii].Value[0])
	// }

	for i := 0; i < e.Parameters.polyExtendFactor; i++ {
		for j := 1; j < e.Parameters.glweRank+1; j++ {
			e.buffer.ctAcc[i].Value[j].Clear()
		}
	}

	for j := 0; j < e.Parameters.polyExtendFactor; j++ {
		e.Decomposer.DecomposePolyAssign(e.buffer.ctAcc[j].Value[0], e.Parameters.blindRotateParameters, polyDecomposed)
		for l := 0; l < e.Parameters.blindRotateParameters.level; l++ {
			e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[l], e.buffer.ctAccFourierDecomposed[j][0][l])
		}
	}

	a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[1])
	a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

	for k := 0; k < e.Parameters.polyExtendFactor; k++ {
		e.GadgetProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[0].Value[0], e.buffer.ctAccFourierDecomposed[k][0], e.buffer.ctBlockFourierAcc[k])
	}

	if a2NIdx == 0 {
		e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
		for k := 0; k < e.Parameters.polyExtendFactor; k++ {
			e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[k], e.buffer.fMono, e.buffer.ctFourierAcc[k])
		}
	} else {
		e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
		for k, kk := 0, e.Parameters.polyExtendFactor-a2NIdx; k < a2NIdx; k, kk = k+1, kk+1 {
			e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
			e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
		}
		e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono, e.buffer.fMono)
		for k, kk := a2NIdx, 0; k < e.Parameters.polyExtendFactor; k, kk = k+1, kk+1 {
			e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
			e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
		}
	}

	for j := 1; j < e.Parameters.blockSize; j++ {
		a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[j+1])
		a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

		for k := 0; k < e.Parameters.polyExtendFactor; k++ {
			e.GadgetProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j].Value[0], e.buffer.ctAccFourierDecomposed[k][0], e.buffer.ctBlockFourierAcc[k])
		}

		if a2NIdx == 0 {
			e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
			for k := 0; k < e.Parameters.polyExtendFactor; k++ {
				e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[k], e.buffer.fMono, e.buffer.ctFourierAcc[k])
			}
		} else {
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
			for k, kk := 0, e.Parameters.polyExtendFactor-a2NIdx; k < a2NIdx; k, kk = k+1, kk+1 {
				e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
			}
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono, e.buffer.fMono)
			for k, kk := a2NIdx, 0; k < e.Parameters.polyExtendFactor; k, kk = k+1, kk+1 {
				e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
			}
		}
	}

	for j := 0; j < e.Parameters.polyExtendFactor; j++ {
		for k := 0; k < e.Parameters.glweRank+1; k++ {
			e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[j].Value[k], e.buffer.ctAcc[j].Value[k])
		}
	}

	for i := 1; i < e.Parameters.blockCount-1; i++ {
		for j := 0; j < e.Parameters.polyExtendFactor; j++ {
			for k := 0; k < e.Parameters.glweRank+1; k++ {
				e.Decomposer.DecomposePolyAssign(e.buffer.ctAcc[j].Value[k], e.Parameters.blindRotateParameters, polyDecomposed)
				for l := 0; l < e.Parameters.blindRotateParameters.level; l++ {
					e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[l], e.buffer.ctAccFourierDecomposed[j][k][l])
				}
			}
		}

		a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[i*e.Parameters.blockSize+1])
		a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

		for k := 0; k < e.Parameters.polyExtendFactor; k++ {
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[i*e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[k], e.buffer.ctBlockFourierAcc[k])
		}

		if a2NIdx == 0 {
			e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
			for k := 0; k < e.Parameters.polyExtendFactor; k++ {
				e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[k], e.buffer.fMono, e.buffer.ctFourierAcc[k])
			}
		} else {
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
			for k, kk := 0, e.Parameters.polyExtendFactor-a2NIdx; k < a2NIdx; k, kk = k+1, kk+1 {
				e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
			}
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono, e.buffer.fMono)
			for k, kk := a2NIdx, 0; k < e.Parameters.polyExtendFactor; k, kk = k+1, kk+1 {
				e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
			}
		}

		for j := i*e.Parameters.blockSize + 1; j < (i+1)*e.Parameters.blockSize; j++ {
			a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[j+1])
			a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

			for k := 0; k < e.Parameters.polyExtendFactor; k++ {
				e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[k], e.buffer.ctBlockFourierAcc[k])
			}

			if a2NIdx == 0 {
				e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
				for k := 0; k < e.Parameters.polyExtendFactor; k++ {
					e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[k], e.buffer.fMono, e.buffer.ctFourierAcc[k])
				}
			} else {
				e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
				for k, kk := 0, e.Parameters.polyExtendFactor-a2NIdx; k < a2NIdx; k, kk = k+1, kk+1 {
					e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
					e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
				}
				e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono, e.buffer.fMono)
				for k, kk := a2NIdx, 0; k < e.Parameters.polyExtendFactor; k, kk = k+1, kk+1 {
					e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[k])
					e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[k], e.buffer.ctBlockFourierAcc[k], e.buffer.ctFourierAcc[k])
				}
			}
		}

		for j := 0; j < e.Parameters.polyExtendFactor; j++ {
			for k := 0; k < e.Parameters.glweRank+1; k++ {
				e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[j].Value[k], e.buffer.ctAcc[j].Value[k])
			}
		}
	}

	for j := 0; j < e.Parameters.polyExtendFactor; j++ {
		for k := 0; k < e.Parameters.glweRank+1; k++ {
			e.Decomposer.DecomposePolyAssign(e.buffer.ctAcc[j].Value[k], e.Parameters.blindRotateParameters, polyDecomposed)
			for l := 0; l < e.Parameters.blindRotateParameters.level; l++ {
				e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[l], e.buffer.ctAccFourierDecomposed[j][k][l])
			}
		}
	}

	a2N = 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[e.Parameters.lweDimension-e.Parameters.blockSize+1])
	a2NMono, a2NIdx = a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

	if a2NIdx == 0 {
		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[e.Parameters.lweDimension-e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
		e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
		e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
	} else {
		kk := e.Parameters.polyExtendFactor - a2NIdx
		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[e.Parameters.lweDimension-e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[e.Parameters.lweDimension-e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[kk], e.buffer.ctBlockFourierAcc[kk])
		e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
		e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[0])
		e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[0], e.buffer.ctBlockFourierAcc[0], e.buffer.ctFourierAcc[0])
	}

	for j := e.Parameters.lweDimension - e.Parameters.blockSize + 1; j < e.Parameters.lweDimension; j++ {
		a2N := 2*e.Parameters.lookUpTableSize - e.ModSwitch(ct.Value[j+1])
		a2NMono, a2NIdx := a2N/e.Parameters.polyExtendFactor, a2N%e.Parameters.polyExtendFactor

		if a2NIdx == 0 {
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
			e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(a2NMono, e.buffer.fMono)
			e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
		} else {
			kk := e.Parameters.polyExtendFactor - a2NIdx
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[kk], e.buffer.ctBlockFourierAcc[kk])
			e.PolyEvaluator.MonomialToFourierPolyAssign(a2NMono+1, e.buffer.fMono)
			e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[kk], e.buffer.fMono, e.buffer.ctFourierAcc[0])
			e.SubFourierGLWEAssign(e.buffer.ctFourierAcc[0], e.buffer.ctBlockFourierAcc[0], e.buffer.ctFourierAcc[0])
		}
	}

	for k := 0; k < e.Parameters.glweRank+1; k++ {
		e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[0].Value[k], e.buffer.ctAcc[0].Value[k])
		ctOut.Value[k].CopyFrom(e.buffer.ctAcc[0].Value[k])
	}
}

// blindRotateCiphertextBlockAssign computes the ciphertext blind rotation when PolyDegree = LookUpTableSize and BlockSize > 1.
// This is equivalent to the blind rotation algorithm using block binary keys, as explained in https://eprint.iacr.org/2023/958.
func (e *Evaluator[T]) blindRotateCiphertextBlockAssign(ct LWECiphertext[T], ctIn GLWECiphertext[T], ctOut GLWECiphertext[T]) {
	polyDecomposed := e.Decomposer.buffer.polyDecomposed[:e.Parameters.blindRotateParameters.level]

	for i := 0; i < e.Parameters.glweRank+1; i++ {
		e.PolyEvaluator.MonomialMulPolyAssign(ctIn.Value[i], -e.ModSwitch(ct.Value[0]), ctOut.Value[i])
	}

	for i := 0; i < e.Parameters.blockCount; i++ {
		for j := 0; j < e.Parameters.glweRank+1; j++ {
			e.Decomposer.DecomposePolyAssign(ctOut.Value[j], e.Parameters.blindRotateParameters, polyDecomposed)
			for k := 0; k < e.Parameters.blindRotateParameters.level; k++ {
				e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[k], e.buffer.ctAccFourierDecomposed[0][j][k])
			}
		}

		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[i*e.Parameters.blockSize], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
		e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[i*e.Parameters.blockSize+1]), e.buffer.fMono)
		e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
		for j := i*e.Parameters.blockSize + 1; j < (i+1)*e.Parameters.blockSize; j++ {
			e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[j], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctBlockFourierAcc[0])
			e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[j+1]), e.buffer.fMono)
			e.FourierPolyMulAddFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])
		}

		for j := 0; j < e.Parameters.glweRank+1; j++ {
			e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[0].Value[j], ctOut.Value[j])
		}
	}
}

// blindRotateCiphertextOriginalAssign computes the ciphertext blind rotation when PolyDegree = LookUpTableSize and BlockSize = 1.
// This is equivalent to the original blind rotation algorithm.
func (e *Evaluator[T]) blindRotateCiphertextOriginalAssign(ct LWECiphertext[T], ctIn GLWECiphertext[T], ctOut GLWECiphertext[T]) {
	polyDecomposed := e.Decomposer.buffer.polyDecomposed[:e.Parameters.blindRotateParameters.level]

	for i := 0; i < e.Parameters.glweRank+1; i++ {
		e.PolyEvaluator.MonomialMulPolyAssign(ctIn.Value[i], -e.ModSwitch(ct.Value[0]), ctOut.Value[i])
	}

	// XXX: randomized blind rotation
	var rotMask []T = nil
	if e.Parameters.RandomizedBlindRotate {
		rotMask = make([]T, e.Parameters.lweDimension)
		e.Encryptor.UniformSampler.SampleVecAssign(rotMask)
		rotMask[e.Parameters.lweDimension-1] = 0
		for i := 0; i < e.Parameters.lweDimension-1; i++ {
			rotMask[e.Parameters.lweDimension-1] -= rotMask[i]
		}
	}

	for i := 0; i < e.Parameters.lweDimension; i++ {
		// XXX: randomized blind rotation
		if e.Parameters.RandomizedBlindRotate {
			for j, mask := 0, int(rotMask[i]); j < e.Parameters.glweRank+1; j++ {
				e.PolyEvaluator.MonomialMulPolyInPlace(ctOut.Value[j], mask)
			}
		}
		// fixed original blind rotation
		//  implemented: (X^-ai-1) * <Decomp(ACC), GGSW> + ACC
		//  should be: <Decomp(ACC*(X^-ai-1)), GGSW> + ACC to reduce noise variance by 2
		exponent := -e.ModSwitch(ct.Value[i+1])
		for j := 0; j < e.Parameters.glweRank+1; j++ {
			e.PolyEvaluator.MonomialMulPolyAssign(ctOut.Value[j], exponent, e.buffer.mono)
			e.PolyEvaluator.SubPolyAssign(e.buffer.mono, ctOut.Value[j], e.buffer.mono)
			e.Decomposer.DecomposePolyAssign(e.buffer.mono, e.Parameters.blindRotateParameters, polyDecomposed)
			for k := 0; k < e.Parameters.blindRotateParameters.level; k++ {
				e.PolyEvaluator.ToFourierPolyAssign(polyDecomposed[k], e.buffer.ctAccFourierDecomposed[0][j][k])
			}
		}
		e.ExternalProductFourierDecomposedFourierGLWEAssign(e.EvaluationKey.BlindRotateKey.Value[i], e.buffer.ctAccFourierDecomposed[0], e.buffer.ctFourierAcc[0])
		// e.PolyEvaluator.MonomialSubOneToFourierPolyAssign(-e.ModSwitch(ct.Value[i+1]), e.buffer.fMono)
		// e.FourierPolyMulFourierGLWEAssign(e.buffer.ctBlockFourierAcc[0], e.buffer.fMono, e.buffer.ctFourierAcc[0])

		for j := 0; j < e.Parameters.glweRank+1; j++ {
			e.PolyEvaluator.ToPolyAddAssignUnsafe(e.buffer.ctFourierAcc[0].Value[j], ctOut.Value[j])
		}
	}
}

// KeySwitchForBootstrap performs the keyswitching using evaulater's evaluation key.
// Input ciphertext should be of length GLWEDimension + 1.
// Output ciphertext will be of length LWEDimension + 1.
func (e *Evaluator[T]) KeySwitchForBootstrap(ct LWECiphertext[T]) LWECiphertext[T] {
	ctOut := NewLWECiphertextCustom[T](e.Parameters.lweDimension)
	e.KeySwitchForBootstrapAssign(ct, ctOut)
	return ctOut
}

// KeySwitchForBootstrapAssign performs the keyswitching using evaulater's evaluation key.
// Input ciphertext should be of length GLWEDimension + 1.
// Output ciphertext should be of length LWEDimension + 1.
func (e *Evaluator[T]) KeySwitchForBootstrapAssign(ct, ctOut LWECiphertext[T]) {
	scalarDecomposed := e.Decomposer.buffer.scalarDecomposed[:e.Parameters.keySwitchParameters.level]

	vec.CopyAssign(ct.Value[:e.Parameters.lweDimension+1], ctOut.Value)
	for i, ii := e.Parameters.lweDimension, 0; i < e.Parameters.glweDimension; i, ii = i+1, ii+1 {
		e.Decomposer.DecomposeScalarAssign(ct.Value[i+1], e.Parameters.keySwitchParameters, scalarDecomposed)
		for j := 0; j < e.Parameters.keySwitchParameters.level; j++ {
			e.ScalarMulAddLWEAssign(e.EvaluationKey.KeySwitchKey.Value[ii].Value[j], scalarDecomposed[j], ctOut)
		}
	}
}

func (e *Evaluator[T]) PublicFunctionalKeySwitchDummy(ct LWECiphertext[T], ctOut GLWECiphertext[T]) {
	scalarDecomposed := e.Decomposer.buffer.scalarDecomposed[:e.Parameters.keySwitchParameters.level]

	for i := range e.Parameters.polyDegree {
		e.Decomposer.DecomposeScalarAssign(ct.Value[i+1], e.Parameters.keySwitchParameters, scalarDecomposed)
		for j := 0; j < e.Parameters.keySwitchParameters.level; j++ {
			e.ScalarMulAddGLWEAssign(e.EvaluationKey.DummyPFKSKey.Value[i].Value[j], scalarDecomposed[j], ctOut)
		}
	}
}

func (e *Evaluator[T]) PublicFunctionalKeySwitchFourierDummy(polys []poly.Poly[T], ctOut GLWECiphertext[T]) {
	for i := range e.Parameters.lweDimension {
		e.GadgetProductAddGLWEAssign(e.EvaluationKey.DummyPFKSKey.ValueFourier[i], polys[i], ctOut)
	}
}
