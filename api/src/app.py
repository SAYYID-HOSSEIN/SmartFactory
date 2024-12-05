from threading import Thread
from typing import Annotated
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import Json
import uvicorn
from fastapi import Body, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from model.alert import Alert
from notification_service import send_notification, retrieve_alerts
from user_settings_service import persist_user_settings, retrieve_user_settings, persist_dashboard_settings, load_dashboard_settings
from database.connection import get_db_connection, query_db_with_params, close_connection
from constants import *
import logging
from model.task import *
from contextlib import asynccontextmanager
import asyncio
import requests
from api_auth import ACCESS_TOKEN_EXPIRE_MINUTES, get_verify_api_key, SECRET_KEY, ALGORITHM, password_context
from model.user import *
from model.report import Report

# TODO: how to import modules from rag directory ??
from model.agent import Answer
from datetime import datetime, timedelta, timezone
from jose import jwt


logging.basicConfig(level=logging.INFO)

tasks = []
tasks_lock = asyncio.Lock()


async def task_scheduler():
    """Central scheduler that runs periodic tasks."""
    while True:
        async with tasks_lock:
            for t in tasks:
                if t.shouldRun():
                    await t.run()
        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to start and stop the scheduler."""
    scheduler_task = asyncio.create_task(task_scheduler())
    try:
        yield 
    finally:
        scheduler_task.cancel()  # Cancel the scheduler on application shutdown
        await scheduler_task  # Ensure it exits cleanly

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/smartfactory/postAlert")
async def post_alert(alert: Alert, api_key: str = Depends(get_verify_api_key(["data"]))):
    """
    Endpoint to post an alert.
    This endpoint receives an alert object and processes it by sending notifications
    based on the alert's properties. It performs several validation checks on the 
    alert object before sending the notification.
    Args:
        alert (Alert): The alert object containing notification details.
    Returns:
        Response: A response object with status code 200 if the notification is sent successfully.
    Raises:
        HTTPException: If any validation check fails or an unexpected error occurs.
    """

    try:
        logging.info("Received alert with title: %s", alert.description)
        
        if not alert.title:
            logging.error("Missing notification title")
            raise HTTPException(status_code=400, detail="Missing notification title")
        
        if not alert.description:
            logging.error("Missing notification description")
            raise HTTPException(status_code=400, detail="Missing notification description")
        
        if not alert.isPush and not alert.isEmail:
            logging.error("No notification method selected")
            raise HTTPException(status_code=400, detail="No notification method selected")
        
        if not alert.recipients or len(alert.recipients) == 0:
            logging.error("No recipients specified")
            raise HTTPException(status_code=400, detail="No recipients specified")
        
        logging.info("Sending notification")
        send_notification(alert)
        logging.info("Notification sent successfully")

        return JSONResponse(content={"message": "Notification sent successfully"}, status_code=200)
    except HTTPException as e:
        logging.error("HTTPException: %s", e.detail)
        raise e
    except ValueError as e:
        logging.error("ValueError: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except TypeError as e:
        logging.error("TypeError: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/smartfactory/alerts/{userId}")
def get_alerts(userId: str, api_key: str = Depends(get_verify_api_key(["gui"]))):
    """
    Retrieve alerts for a given user and return them as a JSON response.

    Args:
        userId (str): The ID of the user for whom to retrieve alerts.

    Returns:
        JSONResponse: A JSON response containing the list of alerts for the user.
    """
    logging.info("Retrieving alerts for user: %s", userId)
    list = retrieve_alerts(userId)
    logging.info("Alerts retrieved successfully for user: %s", userId)

    return JSONResponse(content={"alerts": list}, status_code=200)

@app.post("/smartfactory/settings/{userId}")
def save_user_settings(userId: str, settings: dict, api_key: str = Depends(get_verify_api_key(["gui"]))):
    """
    Endpoint to save user settings.
    This endpoint receives a user ID and a JSON object with the settings to be saved.
    Args:
        userId (str): The ID of the user.
        settings (dict): The settings to be saved.
    Returns:
        Response: A response object with status code 200 if the settings are saved successfully.
    Raises:
        HTTPException: If an unexpected error occurs.
    """
    try:
        if persist_user_settings(userId, settings) == False:
            raise HTTPException(status_code=404, detail="User not found")
        
        return JSONResponse(content={"message": "Settings saved successfully"}, status_code=200)
    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/smartfactory/settings/{userId}")
def get_user_settings(userId: str, api_key: str = Depends(get_verify_api_key(["gui"]))):
    """
    Endpoint to get user settings.
    This endpoint receives a user ID and returns the settings for that user.
    Args:
        userId (str): The ID of the user.
    Returns:
        dict: A dictionary containing the user settings.
    Raises:
        HTTPException: If an unexpected error occurs.
    """
    try:
        settings = retrieve_user_settings(userId)
        return JSONResponse(content=settings, status_code=200)
    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/smartfactory/login")
def login(body: Login, api_key: str = Depends(get_verify_api_key(["gui"]))):
    """
    Endpoint to login a user.
    This endpoint receives the user credentials and logins the user if it is present in the database.
    Args:
        body (LoginModel): the login body object containing the login details.
    Returns:
        UserInfo object with the details of the user logged in.
    Raises:
        HTTPException: If any validation check fails or an unexpected error occurs.
    """
    try:
        connection, cursor = get_db_connection()
        query = "SELECT * FROM Users WHERE "+("Email" if body.isEmail else "Username")+"=%s"
        response = query_db_with_params(cursor, connection, query, (body.user,))

        if not response or not password_context.verify(body.password, response[0][4]):
            logging.error("Invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid username or password")
   
        result = response[0]
        close_connection(connection, cursor)
        logging.info("User logged in successfully")
    
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = jwt.encode(
            {"sub": result[1], "role": result[3], "exp": datetime.now(timezone.utc) + access_token_expires},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        logging.info(result)
        user = UserInfo(userId=result[0], username=result[1], email=result[2], role=result[3], access_token=access_token, site=result[5])
        return JSONResponse(content=user.to_dict(), status_code=200) #TODO change to user
    
    except HTTPException as e:
        logging.error("HTTPException: %s", e.detail)
        close_connection(connection, cursor)
        raise e
    except Exception as e:
        logging.error("Exception: %s", str(e))
        close_connection(connection, cursor)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/smartfactory/logout")
def logout(userId: str, api_key: str = Depends(get_verify_api_key(["gui"]))):
    """
    Endpoint to logout a user.
    This endpoint receives the userId and logouts the user if it is present in the database.
    Args:
        body (userId): the id of the user to logout.
    Returns:
        JSONResponse 200
    Raises:
        HTTPException: If the user is not present in the database.
    """
    try:
        connection, cursor = get_db_connection()
        query = "SELECT UserID FROM Users WHERE UserID=%s"
        response = query_db_with_params(cursor, connection, query, (int(userId),))
        logging.info(response)
        if (len(response) == 0):
            raise HTTPException(status_code=404, detail="User not found")
        #TODO delete auth token client side or db if you decide to add it from db
        close_connection(connection, cursor)
        return JSONResponse(content={"message": "User logged out successfully"}, status_code=200)
    except HTTPException as e:
        logging.error("HTTPException: %s", e.detail)
        close_connection(connection, cursor)
        raise e
    except Exception as e:
        logging.error("Exception: %s", str(e))
        close_connection(connection, cursor)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/smartfactory/register", status_code=status.HTTP_201_CREATED)
def register(body: Register, api_key: str = Depends(get_verify_api_key(["gui"]))):
    """
    Endpoint to register a user.
    This endpoint receives the user info and inserts a new user if it is not present in the database.
    Args:
        body (Register): the user details of the new user.
    Returns:
        UserInfo object with the details of the user created.
    Raises:
        HTTPException: If the user is already present in the database.
    """
    try:
        connection, cursor = get_db_connection()
        # Check if user already exists
        query = "SELECT * FROM Users WHERE Username = %s OR Email = %s"
        response = query_db_with_params(cursor, connection, query, (body.username, body.email))
        user_exists = response
        logging.info(user_exists)

        if user_exists:
            logging.error("User already registered")
            raise HTTPException(status_code=400, detail="User already registered")
        else:
            hashed_password = password_context.hash(body.password)

            # Insert new user into the database
            query_insert = "INSERT INTO Users (Username, Email, Role, Password, SiteName) VALUES (%s, %s, %s, %s, %s) RETURNING UserID;"
            cursor.execute(query_insert, (body.username, body.email, body.role, hashed_password, body.site))
            connection.commit()
            userid = cursor.fetchone()[0]
            close_connection(connection, cursor)
            return UserInfo(userId=str(userid), username=body.username, email=body.email, role=body.role, site=body.site, access_token='')

    except HTTPException as e:
        logging.error("HTTPException: %s", e.detail)
        close_connection(connection, cursor)
        raise e
    except Exception as e:
        logging.error("Exception: %s", str(e))
        close_connection(connection, cursor)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/smartfactory/user/{userId}", status_code=status.HTTP_201_CREATED)
def change_password(userId: str, body: ChangePassword, api_key: str = Depends(get_verify_api_key(["gui"]))):
    """
    Endpoint to change a user's password.
    This endpoint receives the user id and the old password inserted, and updates the user's password if the old password is correct.
    Args:
        body (ChangePassword): the user details of the user, including both the new and old password.
    Returns:
        UserInfo object with the details of the user created.
    Raises:
        HTTPException: If the user is not present in the database, the old password is incorrect, or an unexpected error occurs
    """
    try:
        connection, cursor = get_db_connection()   
        # Check if old password is correct
        query = "SELECT Password FROM Users WHERE UserID = %s"
        response = query_db_with_params(cursor, connection, query, (userId,))
        if not response:
            raise HTTPException(status_code=401, detail="User not found")
        try:
            if not password_context.verify(body.old_password, response[0][0]):
                logging.error("Invalid old password")
                return JSONResponse(content={"message": "Invalid old password"}, status_code=401)
        except ValueError as e:
            logging.error("Password not hashed")
            raise HTTPException(status_code=500, detail=f"Password not hashed: {str(e)}")
                
        hashed_password = password_context.hash(body.new_password)
        # Update user password in the database
        query_update = "UPDATE Users SET password = %s WHERE UserID = %s;"
        cursor.execute(query_update, (hashed_password, userId))
        connection.commit()
        # check if updated correctly
        result = cursor.rowcount
        if result == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        close_connection(connection, cursor)
        return JSONResponse(content={"message": "Password changed successfully"}, status_code=200)
    
    except HTTPException as e:
        logging.error("HTTPException: %s", e.detail)
        close_connection(connection, cursor)
        raise e

    except Exception as e:
        logging.error("Exception: %s", str(e))
        close_connection(connection, cursor)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/smartfactory/dashboardSettings/{userId}")
def retrieve_dashboard_settings(userId: str, api_key: str = Depends(get_verify_api_key(["gui"]))):
    '''
    Endpoint to load dashboard disposition from the Database.
    This endpoint receives a user ID and returns the JSON string containing the (tree-like) disposition of the user's dashboards.
    Args:
        userId (str): The ID of the user of whom to retrieve data.
    Returns:
        dashboard_settings: JSON string containing the dashboard disposition.
    Raises:
        HTTPException: If the settings are not found or an unexpected error occurs.

    '''
    try:
        settings = load_dashboard_settings(userId)
        return JSONResponse(content=settings, status_code=200)
    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
   

@app.post("/smartfactory/dashboardSettings/{userId}")
def post_dashboard_settings(userId: str, dashboard_settings: dict, api_key: str = Depends(get_verify_api_key(["gui"]))):
    '''
    Endpoint to save the dashboard disposition to the Database.
    This endpoint receives a user ID and a JSON string with the dashboard disposition to be saved.
    Args:
        userId (str): The ID of the user.
        dashboard_settings (dict): The dashboard disposition to be saved.
    Returns:
        Response: A response object with status code 200 if the dashboard disposition is saved successfully.
    Raises:
        HTTPException: If an unexpected error occurs.
        
    '''
    try:
        if persist_dashboard_settings(userId, dashboard_settings) == False:
            raise HTTPException(status_code=404, detail="User not found")
        
        return JSONResponse(content={"message": "Settings saved successfully"}, status_code=200)
    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/smartfactory/reports")
def retrieve_reports(userId: int, api_key: str = Depends(get_verify_api_key(["gui"]))):
    try:
        connection, cursor = get_db_connection()   
        query = "SELECT ReportID, Name, Type, FilePath FROM Reports WHERE OwnerID = %s"
        response = query_db_with_params(cursor, connection, query, (userId,))
        if not response or response[0] is None:
            logging.info("No reports for userID %s", str(userId))
            return JSONResponse(content={"data": []}, status_code=200)
        reports = []
        path_to_report = {}
        for row in response:
            reports.append(Report(id=row[0], name=row[1], type=row[2], data="").model_dump()) #TODO remove, just for test
            logging.info(row[3])
            path_to_report[row[3]] = Report(id=row[0], name=row[1], type=row[2], data="")
        close_connection(connection, cursor)
        #TODO get reports from DB
        for path in path_to_report.keys():
            break #TODO set data for each report and add to reports list
        return JSONResponse(content={"data": reports}, status_code=200)
    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/smartfactory/reports/generate", status_code=status.HTTP_201_CREATED)
def generate_report(userId: Annotated[str, Body()], params: Annotated[dict, Body()], is_scheduled = False, api_key: str = Depends(get_verify_api_key(["gui"]))):
    try:
        connection, cursor = get_db_connection()   
        query = "SELECT UserID FROM Users WHERE UserID = %s"
        response = query_db_with_params(cursor, connection, query, (int(userId),))
        if not response:
            logging.error("User not found")
            raise HTTPException(status_code=404, detail="User not found")
        report_prompt = ""
        #TODO call RAG to generate report
        report_data = ""
        #TODO insert report into DB
        filepath = "path"
        query_insert = "INSERT INTO Reports (Name, Type, OwnerId, GeneratedAt, FilePath, SiteName) VALUES (%s, %s, %s, %s, %s, %s) RETURNING ReportID, Name, Type;"
        cursor.execute(query_insert, (params.get("name") or "Report"+datetime.now().strftime("%d_%m_%Y"), params.get("type") or "Standard", int(userId), datetime.now(), filepath, params.get("site") or "Test",))
        connection.commit()
        report_db = cursor.fetchone()
        report = Report(id=report_db[0], name=report_db[1], type=report_db[2], data=report_data)
        close_connection(connection, cursor)
        logging.info(report.model_dump_json)
        return JSONResponse(content={"data": report.model_dump()}, status_code=201)
    except HTTPException as e:
        logging.error("HTTPException: %s", e.detail)
        close_connection(connection, cursor)
        raise e
    except Exception as e:
        logging.error("Exception: %s", str(e))
        close_connection(connection, cursor)
        raise HTTPException(status_code=500, detail=str(e))
    
def generate_and_send_report(userId: str, params: dict, api_key: str):
    logging.info("Started scheduled report generation")
    report = generate_report(userId, params, True, api_key)
    #TODO send email

@app.post("/smartfactory/reports/schedule", status_code=status.HTTP_200_OK)
async def schedule_report(userId: Annotated[str, Body()], params: Annotated[dict, Body()], period: Annotated[SchedulingFrequency, Body()], api_key: str = Depends(get_verify_api_key(["gui"]))):
    try:
        connection, cursor = get_db_connection()   
        query = "SELECT UserID FROM Users WHERE UserID = %s"
        response = query_db_with_params(cursor, connection, query, (int(userId),))
        if not response:
            logging.error("User not found")
            raise HTTPException(status_code=404, detail="User not found")
        close_connection(connection, cursor)
        async with tasks_lock:
            tasks.append(Task(func=generate_and_send_report, args=(userId, params, api_key), delay=period.seconds))
    except HTTPException as e:
        logging.error("HTTPException: %s", e.detail)
        close_connection(connection, cursor)
        raise e
    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/smartfactory/agent", response_model=Answer)
def ai_agent_interaction(userInput: Annotated[str, Body(embed=True)], api_key: str = Depends(get_verify_api_key(["gui"]))):
    """
    Endpoint to interact with the AI agent.
    This endpoint receives user input and forwards it to the AI agent, then returns the generated response.
    
    Args:
        userInput (str): The user input to be processed by the AI agent.
    Returns:
        AgentResponse: The response generated by the AI agent.
    Raises:
        HTTPException: If the input is empty or an unexpected error occurs.
    """
    if not userInput:
        logging.error("Empty input")
        raise HTTPException(status_code=500, detail="Empty user input")
    # TODO: find where to store the env variables and how to retrieve them
    
    RAG_API_ENDPOINT = 'http://rag:8000/agent/chat'
    API_KEY = '06e9b31c-e8d4-4a6a-afe5-fc7b0cc045a7'
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
    }
    body = {
        'userInput': userInput
    }
    try:
        # Send the user input to the RAG API and get the response
        print(f"sending request to RAG API: {body}")
        response = requests.post(RAG_API_ENDPOINT, headers=headers, json = body)
        response.raise_for_status()
        # Send the response to the user 
        answer = response.json()
        return answer

    except Exception as e:
        logging.error("Exception: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")

   