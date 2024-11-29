from fastapi import FastAPI, HTTPException
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import math
import google.generativeai as genai
from IPython.display import display
from IPython.display import Markdown
import textwrap
from mysql.connector import (connection)
import mysql.connector
from mysql.connector import errorcode
import markdown
from bs4 import BeautifulSoup
import re
import pandas as pd
import numpy as np

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


@app.get("/gettext/{inputtext2}")
def querygenerator(inputtext2: str):
    
    structure = '''CREATE DATABASE IF NOT EXISTS employees; 
USE employees;

CREATE TABLE employees (
    emp_no      INT             NOT NULL,
    birth_date  DATE            NOT NULL,
    first_name  VARCHAR(14)     NOT NULL,
    last_name   VARCHAR(16)     NOT NULL,
    gender      ENUM ('M','F')  NOT NULL,    
    hire_date   DATE            NOT NULL,
    PRIMARY KEY (emp_no)
);

CREATE TABLE departments (
    dept_no     CHAR(4)         NOT NULL,
    dept_name   VARCHAR(40)     NOT NULL,
    PRIMARY KEY (dept_no),
    UNIQUE  KEY (dept_name)
);

CREATE TABLE dept_manager (
   emp_no       INT             NOT NULL,
   dept_no      CHAR(4)         NOT NULL,
   from_date    DATE            NOT NULL,
   to_date      DATE            NOT NULL,
   FOREIGN KEY (emp_no)  REFERENCES employees (emp_no)    ON DELETE CASCADE,
   FOREIGN KEY (dept_no) REFERENCES departments (dept_no) ON DELETE CASCADE,
   PRIMARY KEY (emp_no,dept_no)
); 

CREATE TABLE dept_emp (
    emp_no      INT             NOT NULL,
    dept_no     CHAR(4)         NOT NULL,
    from_date   DATE            NOT NULL,
    to_date     DATE            NOT NULL,
    FOREIGN KEY (emp_no)  REFERENCES employees   (emp_no)  ON DELETE CASCADE,
    FOREIGN KEY (dept_no) REFERENCES departments (dept_no) ON DELETE CASCADE,
    PRIMARY KEY (emp_no,dept_no)
);

CREATE TABLE titles (
    emp_no      INT             NOT NULL,
    title       VARCHAR(50)     NOT NULL,
    from_date   DATE            NOT NULL,
    to_date     DATE,
    FOREIGN KEY (emp_no) REFERENCES employees (emp_no) ON DELETE CASCADE,
    PRIMARY KEY (emp_no,title, from_date)
) 
; 

CREATE TABLE salaries (
    emp_no      INT             NOT NULL,
    salary      INT             NOT NULL,
    from_date   DATE            NOT NULL,
    to_date     DATE            NOT NULL,
    FOREIGN KEY (emp_no) REFERENCES employees (emp_no) ON DELETE CASCADE,
    PRIMARY KEY (emp_no, from_date)
) 
;'''
    
    GOOGLE_API_KEY="YOUR GEMINI API KEY"

    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')


    def markdown_to_string(markdown_text):

        html = markdown.markdown(markdown_text)
        
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()

    def gemini(input):
        response = model.generate_content(input,
                                          generation_config = genai.GenerationConfig
                                          (temperature=0.1,))
        output = markdown_to_string(response.text)
        return output

    SqlQuery = gemini("This my sql table Structure"+structure+"give me a sql query only for"+inputtext2+"use joins to connect tables as the module of MySQL doesn't yet support 'LIMIT & IN/ALL/ANY/SOME subquery,"+"Fetch all columns whenever possible"+"without any expaination and comments, also take care of lowercase and upper case word  and only use basic commands")


    def extract_sql_query(input_string):
        input_string = re.sub(r'```sql|```', '', input_string).strip()
        input_string.replace("\n"," ")
        if input_string.startswith('sql\n'):
        
            return input_string[4:].strip()
        else:
            return input_string.strip()
            

    SqlQuery = extract_sql_query(SqlQuery)
        
    def genquery(SqlQuery):
        #SqlQuery = gemini("check if this sqlquery contains these LIMIT & IN/ALL/ANY/SOME subquery which are not support by the server so give a new alternate for this query"+SqlQuery)
        SqlQuery = gemini("remove comments from this query and make it simple and easy without elimination of fields"+SqlQuery+"and check syntax error or field names from the structure"+structure+"give only the query to fetch data from database and remove incode explaination or comments from generated Sql query")
        #SqlQuery = gemini("remove incode explaination or comments from this"+SqlQuery)
    
        SqlQuery = extract_sql_query(SqlQuery)
        
        return SqlQuery    
    

    SqlQuery = genquery(SqlQuery)


    conn = connection.MySQLConnection(
        user='root', 
        passwd='Abhishekmathur',
        host='localhost',
        database='employees',
        auth_plugin='mysql_native_password'
    )
    cur = conn.cursor()

    x=0
    def run(SqlQuery, attempt=1, max_attempts=2):
        try:
            cur.execute(SqlQuery)
            column_names = [description[0] for description in cur.description]
            rows = cur.fetchall()
            data = pd.DataFrame(rows, columns=column_names)
            C_N = str(column_names)

        except Exception as e:
            err = str(e)
            if attempt < max_attempts:
                SqlQuery = gemini(f"Encountered error: {err}. Provide a new query.")
                SqlQuery = extract_sql_query(SqlQuery)
                
                return run(SqlQuery, attempt + 1, max_attempts)
            else:
                print("Max attempts reached. Exiting.")
                return None, None
            
                
                

        return  data,C_N
    

    data,C_N = run(SqlQuery)

    
    if "emp_no" not in data.columns:
        data["emp_no"] = 0
        description = [[0.0], [0.0], [0.0], [0.0], [0.0], [0.0], [0.0], [0.0]]
        

    if "gender" not in data.columns:
        data['gender'] = "No Data"

    description = data['emp_no'].describe()
    description = description.values.tolist() 

    if all(isinstance(sublist, list) for sublist in description):
        for sublist in description:
            for i, value in enumerate(sublist):
                if isinstance(value, float) and math.isnan(value):
                    sublist[i] = 0.0
    else:
        for i, value in enumerate(description):
            if isinstance(value, float) and math.isnan(value):
                description[i] = 0.0   
            
    for index in range(len(description)):
        if isinstance(description[index], np.int64):
            description[index] = int(description[index])       
    
    return {"output": description , "data": data.to_dict(orient='records')}





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

