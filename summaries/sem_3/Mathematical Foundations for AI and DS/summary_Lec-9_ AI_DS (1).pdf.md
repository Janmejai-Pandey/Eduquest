# Summary: Lec-9_ AI_DS (1).pdf
**Subject**: Mathematical Foundations for AI and DS
**Semester**: 3

## Source Lectures (click to open)

- [Lec-9_ AI_DS (1).pdf](https://drive.google.com/file/d/1zQizwE2yEoHI_ZYayavT31Z07gELCUbQ/view)

---

## Summary
The lecture covers the mathematical foundations for Artificial Intelligence and Data Science, focusing on independent random variables, covariance, and correlation coefficient. Independent random variables are defined, and an example is provided to check if two variables are independent. The concept of covariance is introduced, which measures the simultaneous variation of two random variables from their respective means. The formula for covariance is given, and its properties are discussed. The correlation coefficient is also defined, which measures the linear relationship between two random variables. The formula for the correlation coefficient is provided, and its properties are discussed. Examples are given to compute the correlation coefficient between two variables.

## Key Formulae & Equations
1. **Covariance**: \(Cov(X, Y) = E[(X - E(X))(Y - E(Y))] = E(XY) - E(X)E(Y)\)
2. **Correlation Coefficient**: \(r = \frac{Cov(X, Y)}{\sigma_X \sigma_Y} = \frac{E(XY) - E(X)E(Y)}{\sqrt{E(X^2) - [E(X)]^2} \sqrt{E(Y^2) - [E(Y)]^2}}\)
3. **Variance of a Linear Combination**: \(Var(aX \pm bY) = a^2Var(X) + b^2Var(Y) \pm 2abCov(X, Y)\)
4. **Covariance of a Linear Combination**: \(Cov(aX + b, cY + d) = acCov(X, Y)\)

## Important Points
1. Independent random variables have a covariance of 0.
2. The correlation coefficient measures the linear relationship between two variables.
3. The correlation coefficient is independent of change and origin and scale.
4. Two independent random variables are uncorrelated, but two uncorrelated random variables need not be independent.
5. The range of the correlation coefficient is between -1 and 1.
6. The formula for covariance can be simplified to \(Cov(X, Y) = E(XY) - E(X)E(Y)\).
7. The correlation coefficient can be calculated using the formula \(r = \frac{Cov(X, Y)}{\sigma_X \sigma_Y}\).
8. The properties of covariance include linearity and the fact that the covariance of independent variables is 0.

## Quick Memorisation Bullets
* Independent random variables have a covariance of 0.
* Covariance measures the simultaneous variation of two variables.
* The correlation coefficient measures linear relationships.
* The formula for covariance is \(Cov(X, Y) = E(XY) - E(X)E(Y)\).
* The correlation coefficient formula is \(r = \frac{Cov(X, Y)}{\sigma_X \sigma_Y}\).
* The range of the correlation coefficient is -1 to 1.
* Independent variables are uncorrelated, but uncorrelated variables may not be independent.
* The correlation coefficient is scale and origin independent.
* \(Var(aX \pm bY) = a^2Var(X) + b^2Var(Y) \pm 2abCov(X, Y)\).
* \(Cov(aX + b, cY + d) = acCov(X, Y)\).