import numpy as np
import matplotlib.pyplot as plt
from math import erf, sqrt
from io import StringIO

# Attempt to load data from a file; fallback to synthetic data if file missing
cnt = 100000
scale = 2.0**(64)
sigma = 2**43.096932  # full MetaPBS
# sigma = 5431314183818.092 # single BR
# sigma = 10863149405646.712891 # exact single BR
# sigma *= sqrt(3)
fname = "dist-br"
# fname = "dist-singlebr"
# fname = "dist-allbr-fix2"
# fname = "dist-9bits-allbr"
# fname = "dist-pure-9bits-allbr"
# fname = "dist-pure-9bits-allbr-oldbr"
# fname = "dist-pure-9bits-allbr-newbr"
# fname = "dist-pure-9bits-allbr-newbr-skip0"
# fname = "dist-9bits-allbr-fixasm"

cnt = 100000

# fname = "dist-final-9bits-all-fixall"
# fname = "dist-final-9bits-all-oldbr"
# fname = "dist-final-9bits-all-newbr"
fname = "dist-final-9bits-all-fixbr"
# fname = "dist-final-9bits-bronly-oldbr"
# fname = "dist-final-9bits-bronly-newbr"
# fname = "dist-final-9bits-bronly-fixbr"
# fname = "dist-exact"
# fname = "dist-final-try-threebr-newbr"
# fname = "dist-final-try-threebr-newbr-exact"
# fname = "dist-final-try-threebr-newbr-exact-noasm"
file_path = f"/home/msh/HE/meta_fbs/logs/{fname}-{cnt}.txt"
# file_path = f"/home/msh/HE/meta_fbs/logs/rust-again1.txt"
# file_path = f"/home/msh/HE/meta_fbs/logs/rust-allbr.txt"
# fname, file_path = "rust-final-bronly", f"/home/msh/HE/meta_fbs/logs/rust-final-bronly.txt"
# fname, file_path = "rust-singlebr", f"/home/msh/HE/meta_fbs/logs/rust-singlebr.txt"


# fname, file_path = "rebuttal", f"/home/msh/HE/meta_fbs/logs/dist-9bits-all-fixbr-100000-rebuttal.txt"

# with open(file_path, "rb") as f:
#     data = f.read().replace(b"\x00", b"")
# text = data.decode("utf-8")
# data = np.loadtxt(StringIO(text))

data = np.loadtxt(file_path, encoding='utf-8')

data /= scale
sigma_sample = np.std(data, ddof=1)
mean_sample = np.mean(data)
print("count samples =", len(data), ", sample stddev =", sigma_sample, ", mean =", mean_sample)
print("mean/stddev =", mean_sample/sigma_sample)

# Compute histogram
sigma /= scale
bin_cnt = 201
bin_edges = np.linspace(-4.5 * sigma, 4.5 * sigma, bin_cnt + 1) - mean_sample
counts, _ = np.histogram(data, bins=bin_edges, density=True)
bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

print("sample stddev / expected stddev:", sigma_sample/sigma)

# Plot
plt.figure(dpi=300)

# Histogram bars
plt.bar(bin_centers, counts, width=(bin_edges[1] - bin_edges[0]), alpha=0.3, label="Sample distribution", color='red',)

print("Sum of histogram is", sum(counts * (bin_edges[1:] - bin_edges[:-1])))

# Fit expected normal distribution
curve_x = np.linspace(bin_edges[0], bin_edges[-1], 1000)
expected = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((curve_x) / sigma) ** 2) / erf(4.5/sqrt(2))
sample_gaus = (1 / (sigma_sample * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((curve_x - mean_sample) / sigma_sample) ** 2) / erf(4.5/sqrt(2))

# Expected density line
plt.plot(curve_x, sample_gaus, color='red', label="Sample ND", lw=1, ls=':')
plt.plot(curve_x, expected, color='blue', label="Expected ND", lw=1, ls=':')
plt.axvline(x = mean_sample, color='red', ls='-.', label=f"Bias/$\sigma$ = {100*mean_sample/sigma_sample:.2f}%", lw=1)
# plt.axvline(x = 0, color='blue', ls=':')
legend = plt.legend()

plt.ticklabel_format(axis='both', style='sci')
plt.text(2*sigma, 4e5, '$\sigma/\sigma_{expected}$ = ' + f'{sigma_sample/sigma*100:.1f}%')


plt.xlabel("Value")
plt.ylabel("Density")
plt.title("Sample and expected distribution")
plt.tight_layout()

plt.draw()
plt.savefig(f"/home/msh/HE/meta_fbs/logs/{fname}-{cnt}.jpg")