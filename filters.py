# Start with empty filters so scraping won't run until the user sets preferences
# The bot handlers populate this dict when the user issues /set_point, /set_price
# and /set_floor commands.
user_filters = {}
