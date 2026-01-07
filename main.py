import requests
import pandas as pd
import time
import threading
import uuid
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==============================
# APP INIT
# ==============================
app = FastAPI(title="SFDA Drug Export Tool")

BASE_URL = "https://www.sfda.gov.sa/GetDrugs.php?page="
TOTAL_PAGES = 880

# ==============================
# IN-MEMORY JOB STORE (SINGLE CLIENT)
# ==============================
jobs = {}

# ==============================
# CORE FETCH FUNCTION
# ==============================
def fetch_sfda_data(job_id: str):
    job = jobs[job_id]
    job["status"] = "running"
    job["message"] = "Initializing request session..."
    job["last_updated"] = time.time()

    processed_pages = 0
    failed_pages = 0
    all_data = []

    session = requests.Session()
    retries = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    headers = {"User-Agent": "Mozilla/5.0 (SFDA Data Tool)"}

    for page in range(1, TOTAL_PAGES + 1):
        print(f"[BACKEND] ▶ START page {page}")

        job["current_page"] = page
        job["message"] = f"Fetching page {page} of {TOTAL_PAGES}"
        job["last_updated"] = time.time()

        try:
            response = session.get(
                f"{BASE_URL}{page}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                print(f"[BACKEND] ⛔ No results at page {page}, stopping.")
                break

            all_data.extend(results)
            processed_pages += 1

            print(f"[BACKEND] ✅ DONE page {page} | total_done={processed_pages}")

            time.sleep(1.2)

        except Exception as e:
            failed_pages += 1
            print(f"[BACKEND] ❌ FAILED page {page} | error={e}")
            job["message"] = f"Retrying page {page}..."
            time.sleep(3)
            continue

    file_name = f"SFDA_Drugs_{job_id}.xlsx"
    pd.DataFrame(all_data).to_excel(file_name, index=False)

    print("=================================")
    print(f"[SUMMARY] Pages processed successfully: {processed_pages}")
    print(f"[SUMMARY] Pages failed/retried: {failed_pages}")
    print(f"[SUMMARY] Total records collected: {len(all_data)}")
    print("=================================")

    job["status"] = "completed"
    job["file"] = file_name
    job["message"] = "Completed successfully"
    job["last_updated"] = time.time()

# ==============================
# ROUTES
# ==============================

@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>SFDA :: DATA EXTRACTION ENGINE</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-black text-green-400 font-mono">

<div class="min-h-screen flex items-center justify-center">
  <div class="w-full max-w-6xl h-[85vh] border border-red-600 rounded-xl
              bg-black/90 shadow-[0_0_40px_rgba(34,197,94,0.35),0_0_80px_rgba(239,68,68,0.45)]
              flex flex-col">

    <div class="flex justify-between items-center px-8 py-5 border-b border-red-600">
      <div class="text-xl tracking-widest">⚠ SFDA DATA EXTRACTION ENGINE</div>
      <div id="badge" class="px-4 py-1 text-xs bg-gray-800 text-gray-300 rounded-full">
        STANDBY
      </div>
    </div>

    <div class="flex flex-1 gap-6 p-6">

      <div class="w-1/3 space-y-6">
        <button id="startBtn" onclick="startJob()"
          class="w-full bg-green-600 hover:bg-green-500 text-black font-bold py-4 rounded-lg text-lg">
          ▶ INITIATE OPERATION
        </button>

        <div class="border border-green-600 rounded-lg p-4 text-sm space-y-2">
          <div>AI CORE: <span class="animate-pulse">ACTIVE</span></div>
          <div>SECURITY MODE: MAXIMUM</div>
          <div>TRACE ROUTING: ENABLED</div>
        </div>

        <div class="border border-green-600 rounded-lg p-4">
          <div class="text-xs text-gray-400">CURRENT PAGE</div>
          <div id="page" class="text-4xl mt-1">0</div>
        </div>

        <div class="border border-green-600 rounded-lg p-4">
          <div class="text-xs text-gray-400">PROGRESS</div>
          <div id="percent" class="text-2xl mt-1">0%</div>
        </div>
      </div>

      <div class="flex-1 flex flex-col relative overflow-hidden">
        <div class="mb-4">
          <div class="h-4 bg-gray-800 rounded overflow-hidden">
            <div id="bar" class="h-full bg-green-500 animate-pulse transition-all duration-500"
                 style="width:0%"></div>
          </div>
        </div>

        <div style="scrollbar-width: thin;" id="terminal"
          class="h-full border  rounded-lg p-4 border-green-600
         overflow-y-auto overflow-y-hidden
         text-sm whitespace-pre-wrap break-words leading-relaxed ">


          <div>> SYSTEM ONLINE. Awaiting command...</div>
        </div>
      </div>
    </div>
  </div>
</div>

<audio id="alarm">
  <source src="https://actions.google.com/sounds/v1/alarms/alarm_siren.ogg" type="audio/ogg">
</audio>

<script>
let jobId = null;
let lastMessage = "";
let alarmPlayed = false;
const terminal = document.getElementById("terminal");

const phaseLogs = [
  "Establishing secure tunnel...",
  "Analyzing traffic pattern...",
  "Normalizing payload...",
  "Verifying integrity...",
  "Compressing dataset..."
];

function log(msg) {
  terminal.innerHTML += "<div>> " + msg + "</div>";
  terminal.scrollTop = terminal.scrollHeight;
}

function startJob() {
  document.getElementById("startBtn").disabled = true;
  document.getElementById("startBtn").innerText = "OPERATION RUNNING...";
  document.getElementById("badge").innerText = "INFILTRATING";
  document.getElementById("badge").className =
    "px-4 py-1 text-xs rounded-full bg-red-700 text-white animate-pulse";

  log("COMMAND ACCEPTED");
  log("ALLOCATING AI RESOURCES...");

  fetch("/start")
    .then(r => r.json())
    .then(d => {
      jobId = d.job_id;
      log("JOB ID: " + jobId);
      poll();
    });
}

function poll() {
  fetch(`/status/${jobId}`)
    .then(r => r.json())
    .then(d => {
      const percent = Math.floor((d.current_page / d.total_pages) * 100);
      document.getElementById("bar").style.width = percent + "%";
      document.getElementById("percent").innerText = percent + "%";
      document.getElementById("page").innerText = d.current_page;

      if (d.message && d.message !== lastMessage) {
        log(d.message);
        lastMessage = d.message;
      }

      if (Math.random() > 0.75) {
        log(phaseLogs[Math.floor(Math.random() * phaseLogs.length)]);
      }

      if (d.status === "completed") {
        log("OPERATION COMPLETE");
        log("PAYLOAD READY");

        if (!alarmPlayed) {
          const alarm = document.getElementById("alarm");
          alarm.loop = true;
          alarm.volume = 1.0;
          alarm.play();
          alarmPlayed = true;

          setTimeout(() => {
            alarm.loop = false;
            alarm.pause();
            alarm.currentTime = 0;
          }, 15000);
        }

        setTimeout(() => {
          window.location.href = `/download/${jobId}`;
        }, 3000);
      } else {
        setTimeout(poll, 1000);
      }
    });
}
</script>
</body>
</html>
"""

@app.get("/start")
def start_job():
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "queued",
        "current_page": 0,
        "total_pages": TOTAL_PAGES,
        "message": "Job queued",
        "file": None,
        "last_updated": time.time()
    }
    threading.Thread(target=fetch_sfda_data, args=(job_id,)).start()
    return {"job_id": job_id}

@app.get("/status/{job_id}")
def job_status(job_id: str):
    return jobs.get(job_id, {"error": "Invalid job id"})

@app.get("/download/{job_id}")
def download(job_id: str):
    job = jobs.get(job_id)
    if not job or job["status"] != "completed":
        return JSONResponse({"error": "File not ready"})
    return FileResponse(
        job["file"],
        filename="SFDA_Drugs_List.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
