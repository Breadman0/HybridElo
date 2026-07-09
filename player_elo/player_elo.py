import pandas as pd
import numpy as np
import sqlite3
import math
import time

# ===== Constants =====
Q = math.log(10) / 400
HOME_ICE_ADVANTAGE = 50.0
OFFSEASON_REVERSION_RATE = 0.33
TAU_SQ = 350.0
COMMIT_EVERY_N_GAMES = 500   
# ======================

connection = sqlite3.connect('data/historic.db')
conn = connection.cursor()

sql_query = """SELECT game_id, home_team, away_team, season, date FROM HISTORIC ORDER BY date ASC"""
game_df = pd.read_sql(sql_query, connection)
game_df['date'] = pd.to_datetime(game_df['date'])

current_season = None
processed = 0
skipped_games = []
error_games = []
t0 = time.time()

for idx, row_s in enumerate(game_df.itertuples()):
    game_id = row_s.game_id 

    if current_season is None:
        current_season = row_s.season

    
    if current_season == "2019-20+1":  
        break

    if current_season != row_s.season:
        q1 = "SELECT player_id, mu, sigma_sq FROM SKATER_RATINGS"    
        q2 = "SELECT player_id, mu, sigma_sq FROM GOALIE_RATINGS"   
        temp1 = pd.read_sql(q1, connection)
        temp2 = pd.read_sql(q2, connection)
        for row1 in temp1.itertuples():
            new_sigma = row1.sigma_sq + TAU_SQ
            new_mu = row1.mu + OFFSEASON_REVERSION_RATE * (1500 - row1.mu)
            conn.execute(
                "UPDATE SKATER_RATINGS SET mu=?, sigma_sq=? WHERE player_id=?",
                (new_mu, new_sigma, row1.player_id)  # FIX #2
            )
        for row2 in temp2.itertuples():
            new_sigma = row2.sigma_sq + TAU_SQ
            new_mu = row2.mu + OFFSEASON_REVERSION_RATE * (1500 - row2.mu)
            conn.execute(
                "UPDATE GOALIE_RATINGS SET mu=?, sigma_sq=? WHERE player_id=?",
                (new_mu, new_sigma, row2.player_id)  # FIX #2
            )
        current_season = row_s.season

    query1 = """
            SELECT
                msg.player_id, msg.team_id, msg.timeOnIce, msg.home_away, msg.goals,
                msg.assists, msg.takeaways, msg.blocked, msg.shots, msg.hits,
                msg.giveaways, msg.penaltyMinutes, msg.faceoffTaken, msg.faceOffWins,
                sr.mu, sr.sigma_sq
            FROM MASTER_SKATER_GAMES as msg
            JOIN SKATER_RATINGS sr ON msg.player_id = sr.player_id
            WHERE msg.game_id = ?
            """
    query2 = """
            SELECT
                mgg.player_id, mgg.team_id, mgg.timeOnIce, mgg.home_away, mgg.goals_allowed,
                mgg.evenStrengthSavePercentage, mgg.powerPlaySavePercentage,
                gr.mu, gr.sigma_sq
            FROM MASTER_GOALIE_GAMES as mgg
            JOIN GOALIE_RATINGS gr on mgg.player_id = gr.player_id
            WHERE mgg.game_id = ?
            """
    
    player_df = pd.read_sql(query1, connection, params=(game_id,))
    goalie_df = pd.read_sql(query2, connection, params=(game_id,))

    home_aggregate, away_aggregate = [], []
    for row in player_df.itertuples():
        
        if row.timeOnIce == 0:
            continue
        (home_aggregate if row.home_away == 'H' else away_aggregate).append(
            (row.mu, row.sigma_sq, row.timeOnIce / 60)
        )
    for row in goalie_df.itertuples():
        if row.timeOnIce == 0:
            continue
        (home_aggregate if row.home_away == 'H' else away_aggregate).append(
            (row.mu, row.sigma_sq, row.timeOnIce / 60)
        )

    
    if len(home_aggregate) == 0 or len(away_aggregate) == 0:
        skipped_games.append(game_id)
        continue

    try:
        home_aggregate = np.array(home_aggregate)
        away_aggregate = np.array(away_aggregate)

        mu_home = np.sum(home_aggregate[:, 2] * home_aggregate[:, 0]) / np.sum(home_aggregate[:, 2]) + HOME_ICE_ADVANTAGE
        mu_away = np.sum(away_aggregate[:, 2] * away_aggregate[:, 0]) / np.sum(away_aggregate[:, 2])
        variancesq_home = np.sum(home_aggregate[:, 2] * home_aggregate[:, 1]) / np.sum(home_aggregate[:, 2])
        variancesq_away = np.sum(away_aggregate[:, 2] * away_aggregate[:, 1]) / np.sum(away_aggregate[:, 2])
        

        for row in player_df.itertuples():
            if row.timeOnIce == 0:
                continue
            if row.home_away == "H":
                var = variancesq_away
                g = 1 / math.sqrt(1 + (3 * (Q ** 2) * var) / (math.pi ** 2))
                Expected_score = 1 / (1 + 10 ** (-(g * (row.mu - mu_away)) / 400))
            else:
                var = variancesq_home
                g = 1 / math.sqrt(1 + (3 * (Q ** 2) * var) / (math.pi ** 2))
                Expected_score = 1 / (1 + 10 ** (-(g * (row.mu - mu_home)) / 400))

            face_off_losses = row.faceoffTaken - row.faceOffWins
            net_face_off = row.faceOffWins - face_off_losses
            fo_term = 0.15*net_face_off
        
            rgi = (4 * row.goals + 2.5 * row.assists + 0.75 * row.takeaways + 0.5 * row.blocked
                   + 0.75 * row.shots + 0.25 * row.hits + fo_term
                   - 1.0 * row.giveaways - 0.25 * row.penaltyMinutes)
            raw_rate_per_60 = (rgi * 3600) / max(row.timeOnIce, 600)
            toi_weight = min(row.timeOnIce/1200,1.0)
            ser = (raw_rate_per_60*0.70) + (rgi*toi_weight*10.0*0.3)
            s_i = 1 / (1 + math.exp(-0.05 * ser))

            estimated_variance = 1 / ((Q ** 2) * (g ** 2) * Expected_score * (1 - Expected_score))
            new_sigma = 1 / ((1 / row.sigma_sq) + (1 / estimated_variance))
            if new_sigma > 400:
                new_sigma = 400
            new_mu = row.mu + Q * new_sigma * g * (s_i - Expected_score)
            conn.execute(
                "UPDATE SKATER_RATINGS SET mu=?, sigma_sq=?, last_updated_game_id=? WHERE player_id=?",
                (new_mu, new_sigma, game_id, row.player_id)
            )

        for row in goalie_df.itertuples():
            if row.timeOnIce == 0:
                continue
            if row.home_away == "H":
                var = variancesq_away
                g = 1 / math.sqrt(1 + (3 * (Q ** 2) * var) / (math.pi ** 2))
                Expected_score = 1 / (1 + 10 ** (-(g * (row.mu - mu_away)) / 400))
            else:
                var = variancesq_home
                g = 1 / math.sqrt(1 + (3 * (Q ** 2) * var) / (math.pi ** 2))
                Expected_score = 1 / (1 + 10 ** (-(g * (row.mu - mu_home)) / 400))

            ev_pct = row.evenStrengthSavePercentage / 100.0 if pd.notna(row.evenStrengthSavePercentage) else 0.90
            pp_pct = row.powerPlaySavePercentage / 100.0 if pd.notna(row.powerPlaySavePercentage) else 0.90
            ga_per_hour = row.goals_allowed / (max(row.timeOnIce, 60) / 3600)
            gei = (2.0 * ev_pct) + (2.5 * pp_pct) - (1.0 * ga_per_hour)
            s_i = 1 / (1 + math.exp(-0.1 * gei))

            estimated_variance = 1 / ((Q ** 2) * (g ** 2) * Expected_score * (1 - Expected_score))
            new_sigma = 1 / ((1 / row.sigma_sq) + (1 / estimated_variance))
            if new_sigma > 400:
                new_sigma = 400
            new_mu = row.mu + Q * new_sigma * g * (s_i - Expected_score)
            conn.execute(
                "UPDATE GOALIE_RATINGS SET mu=?, sigma_sq=?, last_updated_game_id=? WHERE player_id=?",
                (new_mu, new_sigma, game_id, row.player_id)
            )

        processed += 1

    except Exception as e:
        error_games.append((game_id, str(e)))
        continue

    if processed % COMMIT_EVERY_N_GAMES == 0:
        connection.commit()
        print(f"  ...{processed} games processed, {time.time()-t0:.1f}s elapsed")

connection.commit()
t1 = time.time()
print(f"\nDone. Processed {processed} games in {t1-t0:.1f}s.")
print(f"Skipped (no player data logged): {len(skipped_games)} -> {skipped_games}")
print(f"Errored games: {len(error_games)} -> {error_games}")
connection.close()

