package tfhe

import (
	"runtime"
	"sync"

	"github.com/sp301415/tfhe-go/math/num"
	"github.com/sp301415/tfhe-go/math/vec"
)

// GenEvaluationKey samples a new evaluation key for bootstrapping.
//
// This can take a long time.
// Use [*Encryptor.GenEvaluationKeyParallel] for better key generation performance.
func (e *Encryptor[T]) GenEvaluationKey() EvaluationKey[T] {
	return EvaluationKey[T]{
		BlindRotateKey: e.GenBlindRotateKey(),
		KeySwitchKey:   e.GenKeySwitchKeyForBootstrap(),
	}
}

// GenEvaluationKeyParallel samples a new evaluation key for bootstrapping in parallel.
func (e *Encryptor[T]) GenEvaluationKeyParallel() EvaluationKey[T] {
	return EvaluationKey[T]{
		BlindRotateKey: e.GenBlindRotateKeyParallel(),
		KeySwitchKey:   e.GenKeySwitchKeyForBootstrapParallel(),
		TruncationKey:  e.GenTruncationKeyParallel(),
		DummyPFKSKey:   e.GenDummyPFKSKey(),
	}
}

// GenBlindRotateKey samples a new bootstrapping key.
//
// This can take a long time.
// Use [*Encryptor.GenBlindRotateKeyParallel] for better key generation performance.
func (e *Encryptor[T]) GenBlindRotateKey() BlindRotateKey[T] {
	brk := NewBlindRotateKey(e.Parameters)

	for i := 0; i < e.Parameters.lweDimension; i++ {
		for j := 0; j < e.Parameters.glweRank+1; j++ {
			if j == 0 {
				e.buffer.ptGGSW.Clear()
				e.buffer.ptGGSW.Coeffs[0] = e.SecretKey.LWEKey.Value[i]
			} else {
				e.PolyEvaluator.ScalarMulPolyAssign(e.SecretKey.GLWEKey.Value[j-1], e.SecretKey.LWEKey.Value[i], e.buffer.ptGGSW)
			}
			for k := 0; k < e.Parameters.blindRotateParameters.level; k++ {
				e.PolyEvaluator.ScalarMulPolyAssign(e.buffer.ptGGSW, e.Parameters.blindRotateParameters.BaseQ(k), e.buffer.ctGLWE.Value[0])
				e.EncryptGLWEBody(e.buffer.ctGLWE)
				e.ToFourierGLWECiphertextAssign(e.buffer.ctGLWE, brk.Value[i].Value[j].Value[k])
			}
		}
	}

	return brk
}

// GenBlindRotateKeyParallel samples a new bootstrapping key in parallel.
func (e *Encryptor[T]) GenBlindRotateKeyParallel() BlindRotateKey[T] {
	brk := NewBlindRotateKey(e.Parameters)

	workSize := e.Parameters.lweDimension * (e.Parameters.glweRank + 1)
	chunkCount := num.Min(runtime.NumCPU(), num.Sqrt(workSize))

	encryptorPool := make([]*Encryptor[T], chunkCount)
	for i := range encryptorPool {
		encryptorPool[i] = e.ShallowCopy()
	}

	jobs := make(chan [2]int)
	go func() {
		defer close(jobs)
		for i := 0; i < e.Parameters.lweDimension; i++ {
			for j := 0; j < e.Parameters.glweRank+1; j++ {
				jobs <- [2]int{i, j}
			}
		}
	}()

	var wg sync.WaitGroup
	wg.Add(chunkCount)
	for i := 0; i < chunkCount; i++ {
		go func(i int) {
			eIdx := encryptorPool[i]
			for job := range jobs {
				i, j := job[0], job[1]

				if j == 0 {
					eIdx.buffer.ptGGSW.Clear()
					eIdx.buffer.ptGGSW.Coeffs[0] = eIdx.SecretKey.LWEKey.Value[i]
				} else {
					eIdx.PolyEvaluator.ScalarMulPolyAssign(eIdx.SecretKey.GLWEKey.Value[j-1], eIdx.SecretKey.LWEKey.Value[i], eIdx.buffer.ptGGSW)
				}
				for k := 0; k < eIdx.Parameters.blindRotateParameters.level; k++ {
					eIdx.PolyEvaluator.ScalarMulPolyAssign(eIdx.buffer.ptGGSW, eIdx.Parameters.blindRotateParameters.BaseQ(k), eIdx.buffer.ctGLWE.Value[0])
					eIdx.EncryptGLWEBody(eIdx.buffer.ctGLWE)
					eIdx.ToFourierGLWECiphertextAssign(eIdx.buffer.ctGLWE, brk.Value[i].Value[j].Value[k])
				}
			}
			wg.Done()
		}(i)
	}
	wg.Wait()

	return brk
}

// GenTruncationKeyParallel samples a new truncation key in parallel.
//
// Shifts by X^(i*repeatBase) are contained in truncation keys
//
// Note that truncationBound does not affect the encrypted values of truncation keys
func (e *Encryptor[T]) GenTruncationKeyParallel() (trks []TruncationKey[T]) {
	p := e.Parameters
	trks = NewTruncationKeys(p)
	if trks == nil {
		return nil
	}

	iters := p.itersCount
	repeatBase := p.repeatBase
	extendCoeffsCount := p.extendedCoeffsCount
	N := p.polyDegree

	totalTruncRepeats := p.CountTruncRepeats()

	for truncIdx := range totalTruncRepeats {
		found := false
		// reuse previous truncation keys if possible, except for the last truncRepeat in Meta-FDFB
		for i := range min(truncIdx, iters) {
			if trks[truncIdx].GadgetParameters == trks[i].GadgetParameters &&
				trks[truncIdx].repeatBase == trks[i].repeatBase &&
				trks[truncIdx].extendCoefffsCount == trks[i].extendCoefffsCount {
				trks[truncIdx] = trks[i]
				found = true
				break
			}
		}
		if found {
			continue
		}

		lastTrFDFB := truncIdx == iters+1

		workSize := len(trks[truncIdx].Value)
		chunkCount := num.Min(runtime.NumCPU(), num.Sqrt(workSize))

		encryptorPool := make([]*Encryptor[T], chunkCount)
		for i := range encryptorPool {
			encryptorPool[i] = e.ShallowCopy()
		}

		jobs := make(chan int)
		go func() {
			defer close(jobs)
			for i := range trks[truncIdx].Value {
				jobs <- i
			}
		}()

		var wg sync.WaitGroup
		wg.Add(chunkCount)
		for i := range chunkCount {
			go func(i int) {
				eIdx := encryptorPool[i]
				// i is shadowed from now on
				for i := range jobs {
					// i = RLWE secret segment index
					// truncate secret coeffs to [lo, hi]
					eIdx.buffer.ptGGSW.Clear()
					lo := i * (extendCoeffsCount[truncIdx] + 1)
					hi := min(lo+extendCoeffsCount[truncIdx], N-1)
					curBase := repeatBase[truncIdx]
					// no repetition polynomial or offset for last truncRepeat in FDFB
					if lastTrFDFB {
						for jj := lo; jj <= hi; jj++ {
							kk := (jj - lo) * curBase
							eIdx.buffer.ptGGSW.Coeffs[kk] = eIdx.SecretKey.GLWEKey.Value[0].Coeffs[jj]
						}
					} else {
						// (1+X+...+X^(repeatBase-1)) * ((partial secret)(X^repeatBase))
						// offset := -curBase / 2
						for jj := lo; jj <= hi; jj++ {
							for kk := (jj - lo) * curBase; kk < (jj-lo+1)*curBase; kk++ {
								eIdx.buffer.ptGGSW.Coeffs[kk] = eIdx.SecretKey.GLWEKey.Value[0].Coeffs[jj]
							}
						}
					}
					// vec.RotateInPlaceNegacyclic(eIdx.buffer.ptGGSW.Coeffs, offset)
					for k := 0; k < trks[truncIdx].GadgetParameters.level; k++ {
						eIdx.PolyEvaluator.ScalarMulPolyAssign(eIdx.buffer.ptGGSW, trks[truncIdx].GadgetParameters.BaseQ(k), eIdx.buffer.ctGLWE.Value[0])
						eIdx.EncryptGLWEBody(eIdx.buffer.ctGLWE)
						eIdx.ToFourierGLWECiphertextAssign(eIdx.buffer.ctGLWE, trks[truncIdx].Value[i].Value[k])
					}
				}
				wg.Done()
			}(i)
		}
		wg.Wait()
	}

	return trks
}

func (e *Encryptor[T]) GenDummyPFKSKey() DummyPFKSKey[T] {
	if !e.Parameters.isDummyPublicFunctionalKeySwitch {
		return DummyPFKSKey[T]{}
	}
	N := e.Parameters.polyDegree
	n := e.Parameters.lweDimension
	pfksk := NewDummyPFKSKey(e.Parameters)
	for i := range N {
		pfksk.Value[i] = e.EncryptGLevPoly(e.buffer.ptGGSW, pfksk.GadgetParameters)
	}
	for i := range n {
		pfksk.ValueFourier[i] = e.EncryptFourierGLevPoly(e.buffer.ptGGSW, pfksk.GadgetParameters)
	}
	return pfksk
}

// GenKeySwitchKeyForBootstrap samples a new keyswitch key LWELargeKey -> LWEKey,
// used for bootstrapping.
//
// This can take a long time.
// Use [*Encryptor.GenKeySwitchKeyForBootstrapParallel] for better key generation performance.
func (e *Encryptor[T]) GenKeySwitchKeyForBootstrap() LWEKeySwitchKey[T] {
	skIn := LWESecretKey[T]{Value: e.SecretKey.LWELargeKey.Value[e.Parameters.lweDimension:]}
	ksk := NewKeySwitchKeyForBootstrap(e.Parameters)

	for i := 0; i < ksk.InputLWEDimension(); i++ {
		for j := 0; j < e.Parameters.keySwitchParameters.level; j++ {
			ksk.Value[i].Value[j].Value[0] = skIn.Value[i] << e.Parameters.keySwitchParameters.LogBaseQ(j)

			e.UniformSampler.SampleVecAssign(ksk.Value[i].Value[j].Value[1:])
			ksk.Value[i].Value[j].Value[0] += -vec.Dot(ksk.Value[i].Value[j].Value[1:], e.SecretKey.LWEKey.Value)
			ksk.Value[i].Value[j].Value[0] += e.GaussianSampler.Sample(e.Parameters.LWEStdDevQ())
		}
	}

	return ksk
}

// GenKeySwitchKeyForBootstrapParallel samples a new keyswitch key LWELargeKey -> LWEKey in parallel,
// used for bootstrapping.
func (e *Encryptor[T]) GenKeySwitchKeyForBootstrapParallel() LWEKeySwitchKey[T] {
	skIn := LWESecretKey[T]{Value: e.SecretKey.LWELargeKey.Value[e.Parameters.lweDimension:]}
	ksk := NewKeySwitchKeyForBootstrap(e.Parameters)

	workSize := ksk.InputLWEDimension() * e.Parameters.keySwitchParameters.level
	chunkCount := num.Min(runtime.NumCPU(), num.Sqrt(workSize))

	encryptorPool := make([]*Encryptor[T], chunkCount)
	for i := range encryptorPool {
		encryptorPool[i] = e.ShallowCopy()
	}

	jobs := make(chan [2]int)
	go func() {
		defer close(jobs)
		for i := 0; i < ksk.InputLWEDimension(); i++ {
			for j := 0; j < e.Parameters.keySwitchParameters.level; j++ {
				jobs <- [2]int{i, j}
			}
		}
	}()

	var wg sync.WaitGroup
	wg.Add(chunkCount)
	for i := 0; i < chunkCount; i++ {
		go func(i int) {
			eIdx := encryptorPool[i]
			for jobs := range jobs {
				i, j := jobs[0], jobs[1]
				ksk.Value[i].Value[j].Value[0] = skIn.Value[i] << eIdx.Parameters.keySwitchParameters.LogBaseQ(j)
				eIdx.UniformSampler.SampleVecAssign(ksk.Value[i].Value[j].Value[1:])
				ksk.Value[i].Value[j].Value[0] += -vec.Dot(ksk.Value[i].Value[j].Value[1:], eIdx.SecretKey.LWEKey.Value)
				ksk.Value[i].Value[j].Value[0] += eIdx.GaussianSampler.Sample(eIdx.Parameters.LWEStdDevQ())
			}
			wg.Done()
		}(i)
	}
	wg.Wait()

	return ksk
}
