# Bayesian NHL Performance Engine

## 🚀 Overview
The **Bayesian NHL Performance Engine** is a high-performance statistical framework designed to estimate the latent skill of professional hockey players over time. 

Unlike traditional hockey metrics like GAR or WAR—which quantify value retrospectively—this engine treats player skill as a **dynamic, evolving latent state**. By utilizing a modified **Glicko-based Bayesian updater**, the system calculates a player's rating ($\mu$) and uncertainty ($\sigma^2$) in real-time, allowing for predictive modeling that adapts to player form, injuries, and generational talent emergence.

## 🧠 Key Innovations
* **Bayesian Individual Matchup Lens:** Instead of treating teams as monolithic entities, the engine dynamically collapses roster data into **TOI-Weighted Team Proxies** for every specific game.
* **Veteran Uncertainty Cage Breaking:** Implements a controlled variance floor and summer-entropy injection ($\tau^2$) to prevent veteran ratings from stagnating, while allowing rookies to achieve rapid convergence.
* **Continuous Box-Score Alchemy:** Maps raw hockey statistics (Goals, Assists, TOI, etc.) to a probability scalar ($s_i$) via a logistic sigmoid, ensuring individual contributions are contextually scaled against the opponent's quality.

## 📊 System Architecture
The engine processes historical game logs through a four-phase chronological pipeline:
1. **Offseason Entropy:** Simulates seasonal decay and resets uncertainty.
2. **Contextual Projection:** Collapses active rosters into opponent-adjusted expectation anchors.
3. **Performance Translation:** Maps game impact to an efficiency probability.
4. **Bayesian State Update:** Adjusts player beliefs based on the delta between expectation and reality.

## 🛠️ Tech Stack
* **Language:** Python 3.14+
* **Database:** SQLite (Flattened, high-performance schema)
* **Mathematical Core:** SciPy/NumPy-optimized Bayesian inference
* **Validation:** Spearman's Rank Correlation ($\rho = 0.39$, $p < 0.001$) against decade-long expert consensus.

## 📈 Performance Summary
The model successfully reconstructs the consensus elite performers of the 2010–2020 era without explicit bias, relying solely on game-play data. It maintains a **0.392 Spearman Rank Correlation** with independent expert rankings, proving the model captures a highly significant, non-random signal of on-ice impact.

## 📖 Documentation
For a deep dive into the underlying derivation, hyperparameter selection, and assumptions, see the formal architectural documentation in the `/docs` folder

*Disclaimer: This project is an independent research endeavor aimed at statistical evaluation and predictive modeling.*
