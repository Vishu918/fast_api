from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from databases import Database
from pymongo import MongoClient
from dotenv import dotenv_values

app = FastAPI()

# Load environment variables
env = dotenv_values(".env")

# PostgreSQL configuration
DATABASE_URL = env.get("DATABASE_URL")
database = Database(DATABASE_URL)

# MongoDB configuration
MONGO_CONNECTION_STRING = env.get("MONGO_CONNECTION_STRING")
mongo_client = MongoClient(MONGO_CONNECTION_STRING)
mongo_db = mongo_client[env.get("MONGO_DB_NAME")]
mongo_collection = mongo_db[env.get("MONGO_COLLECTION_NAME")]

# Pydantic model for user registration
class UserRegistration(BaseModel):
    full_name: str
    email: str
    password: str
    phone: str
    profile_picture: str

# Route to check if email already exists in PostgreSQL
def check_email_exists(email: str):
    query = "SELECT email FROM users WHERE email = :email"
    result = database.fetch_one(query=query, values={"email": email})
    return result

# Route to handle user registration
@app.post("/register/", status_code=201)
def register_user(user: UserRegistration):
    # Check if the email already exists in PostgreSQL
    email_exists = check_email_exists(user.email)
    if email_exists:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Insert user data into PostgreSQL
    query = """
        INSERT INTO users (first_name, password, email, phone)
        VALUES (:first_name, :password, :email, :phone)
        RETURNING id
    """
    values = {
        "first_name": user.full_name.split()[0],
        "password": user.password,
        "email": user.email,
        "phone": user.phone,
    }
    user_id = database.fetch_val(query=query, values=values)

    # Save profile picture in MongoDB
    mongo_collection.insert_one({"user_id": user_id, "profile_picture": user.profile_picture})

    return {"user_id": user_id}

# Run the database connection when the app starts
@app.on_event("startup")
def startup():
    database.connect()

# Close the database connection when the app stops
@app.on_event("shutdown")
def shutdown():
    database.disconnect()

# Run the FastAPI app with uvicorn
if __name__ == "__main__":
    import os

    os.environ["DATABASE_URL"] = env.get("DATABASE_URL")
    os.environ["MONGO_CONNECTION_STRING"] = env.get("MONGO_CONNECTION_STRING")
    os.environ["MONGO_DB_NAME"] = env.get("MONGO_DB_NAME")
    os.environ["MONGO_COLLECTION_NAME"] = env.get("MONGO_COLLECTION_NAME")

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
