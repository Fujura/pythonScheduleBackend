from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import io
from pydantic import BaseModel
import docx
from datetime import datetime

app = FastAPI()
origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class ScheduleRequest(BaseModel):
    group: str
    shift: int


def parse_docx(file):
    doc = docx.Document(io.BytesIO(file))
    schedule = []
    for table in doc.tables:
        for row in table.rows:
            schedule_row = [cell.text.strip() for cell in row.cells]
            schedule.append(schedule_row)
    return schedule

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.filename.endswith('.docx'):
        try:
            schedule_data = parse_docx(await file.read())
            now = datetime.now()
            file_date = file.filename.split()[0]
            formatted_date = datetime.strptime(file_date, "%d.%m.%Y").strftime("%Y-%m-%d")
            json_file_path = os.path.join("uploaded_schedules", "raspisanie.json")
            if os.path.exists(json_file_path):
                os.remove(json_file_path)
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(schedule_data, f, ensure_ascii=False, indent=4)
            return JSONResponse(content={"schedule": schedule_data}, status_code=200)
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)
    else:
        return JSONResponse(content={"error": "Only .docx files are supported"}, status_code=400)

def get_schedule_from_file():
    try:
        with open("uploaded_schedules/raspisanie.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def get_fisrtshift_time(index):
    if index <= 2:
        return "08:00 - 09:20, 1 пара"
    elif index <= 4:
        return "09:30 - 10:50, 2 пара"
    elif index <= 6:
        return "11:05 - 12:25, 3 пара"
    elif index <= 8:
        return "12:55 - 14:15, 4 пара"
    else:
        return "not found"


def get_secondshift_time(index):
    if index == 2:
        return "12:55 - 14:15, 1 пара"
    elif index <= 4:
        return "14:25 - 15:45, 2 пара"
    elif index <= 6:
        return "16:00 - 17:20, 3 пара"
    elif index <= 8:
        return "17:30 - 18:20, 4 пара"
    else:
        return "not found"
current_id = 1

@app.post("/schedule")
async def get_group_schedule(request: Request):
    global current_id

    data = await request.json()
    group = data.get("group")
    shift = data.get("shift")

    if not group:
        raise HTTPException(status_code=400, detail="нет такой группы")
    if not shift:
        raise HTTPException(status_code=400, detail="не указана смена")
    timetable = get_schedule_from_file()

    schedule = []

    for line in timetable:
        # Проверяем каждую строку расписания на наличие группы
        for idx, value in enumerate(line):
            if group in value:
                cabinet = line[0]
                if shift == 1:
                    time = get_fisrtshift_time(idx)
                elif shift == 2:
                    time = get_secondshift_time(idx)
                lesson_info = {
                    "id": current_id,
                    "group": group,
                    "cabinet": cabinet,
                    "teacher": line[idx - 1],
                    "time": time
                }

                schedule.append(lesson_info)
                current_id += 1

    if schedule:
        return schedule
    raise HTTPException(status_code=404, detail="урок для данной группы не найден")



@app.post("/alice_schedule")
async def run_cript(request: Request, schedule_request: ScheduleRequest):
   data = schedule_request.dict()
   group = data.get("group")
   shift = data.get("shift")

   if not group:
       raise HTTPException(status_code=400, detail="Вы не указали название группы.")

   if not shift:
       raise HTTPException(status_code=400, detail="Вы не указали номер смены.")

   timetable = get_schedule_from_file()
   schedule = []

   for line in timetable:
       for idx, value in enumerate(line):
           if group in value:
               cabinet = line[0]
               if shift == 1:
                   time = get_fisrtshift_time(idx)
               elif shift == 2:
                   time = get_secondshift_time(idx)
               lesson_info = {
                   "id": current_id,
                   "group": group,
                   "cabinet": cabinet,
                   "teacher": line[idx - 1],
                   "time": time
               }
               schedule.append(lesson_info)
               current_id += 1

   if schedule:
       response_text = "Расписание:\n"
       for lesson in schedule:
           response_text += f"Группа {lesson['group']}, Кабинет {lesson['cabinet']}, Преподаватель {lesson['teacher']}, Время {lesson['time']}\n"
       return JSONResponse(content={"text": response_text}, status_code=200)
   else:
       return JSONResponse(content={"text": "Уроки для указанной группы не найдены."}, status_code=200)