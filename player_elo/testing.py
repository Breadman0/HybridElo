import pandas as pd
import numpy as np 
import sqlite3
import math

connection = sqlite3.connect('data\historic.db')
conn = connection.cursor()

query = """
SELECT sr.player_id , sr.mu , sr.sigma_sq , pi.firstName , pi.lastName
FROM SKATER_RATINGS AS sr
JOIN PLAYER_INFO as pi ON sr.player_id = pi.player_id
"""
player_df = pd.read_sql(query,connection)
player_df['sigma'] = np.sqrt(player_df['sigma_sq'])
player_df['con_rating'] = player_df['mu'] - (2 * player_df['sigma'])
player_df = player_df.sort_values(by='con_rating',ascending=False)


print(player_df[['firstName','lastName','con_rating']].head(100))
player_df.to_csv("player_elo/top100.csv",index=False)

query_2 = """
SELECT gr.player_id , gr.mu ,  gr.sigma_sq , pi.firstName , pi.lastName
FROM GOALIE_RATINGS AS gr
JOIN PLAYER_INFO as pi on gr.player_id = pi.player_id
"""
goalie_df = pd.read_sql(query_2,connection)
goalie_df['sigma'] = np.sqrt(goalie_df['sigma_sq'])
goalie_df['con_rating'] = goalie_df['mu'] - (2*goalie_df['sigma'])
goalie_df = goalie_df.sort_values(by='con_rating',ascending=False)
print(goalie_df[['firstName','lastName','con_rating']].head(30))
goalie_df.to_csv("player_elo/top30.csv",index=False)
connection.close()

