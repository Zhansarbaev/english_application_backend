from utils import create_reset_token

email = "zhansarbaevvv@gmail.com"  
token = create_reset_token(email)

print("JWT Token:", token)
