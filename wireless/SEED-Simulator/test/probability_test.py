import numpy as np
from scipy.stats import norm
from scipy.stats import lognorm


def convertMuSigmaFromLogNormalToNormal(mu, sigma):
        norm_mu = 2*np.log(mu) - np.log(sigma**2 + mu**2)/2
        norm_sigma = -2*np.log(mu) + np.log(sigma**2 + mu**2)
        print(norm_mu, norm_sigma)
        return norm_mu, norm_sigma

mu_ln_shadowing = 5
sigma_ln_shadowing = 6
mu_ln_nlosv = 0
sigma_ln_nlosv = 4

mu_shadowing, sigma_shadowing = convertMuSigmaFromLogNormalToNormal(mu_ln_shadowing, sigma_ln_shadowing)
mu_nlosv, sigma_nlosv = convertMuSigmaFromLogNormalToNormal(mu_ln_nlosv, sigma_ln_nlosv)

print(norm.cdf(10, loc=mu_nlosv, scale=sigma_nlosv))
# print(norm.cdf(10, s=sigma_nlosv, mu=mu_nlosv))
print(lognorm.cdf(10, s=sigma_ln_nlosv, scale=np.exp(mu_ln_nlosv)))

mu_sum = mu_shadowing + mu_nlosv
sigma_sum = np.sqrt(sigma_shadowing**2 + sigma_nlosv**2)

newThreshold = 10
# lossRate = 1- norm.cdf(newThreshold, sigma=sigma_sum, mu=mu_sum) * 100