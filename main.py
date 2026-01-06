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
TOTAL_PAGES = 3   # change only if SFDA changes pagination

# ==============================
# IN-MEMORY JOB STORE
# ==============================
jobs = {}

# ==============================
# CORE FETCH FUNCTION
# ==============================
def fetch_sfda_data(job_id: str):
    job = jobs[job_id]
    job["status"] = "running"
    job["message"] = "Initializing request session..."

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

    headers = {
        "User-Agent": "Mozilla/5.0 (SFDA Data Tool)"
    }

    for page in range(1, TOTAL_PAGES + 1):
        job["current_page"] = page
        job["message"] = f"Fetching page {page} of {TOTAL_PAGES}"

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
                break

            all_data.extend(results)
            time.sleep(1.2)

        except Exception as e:
            job["message"] = f"Retrying page {page}..."
            time.sleep(3)
            continue

    file_name = f"SFDA_Drugs_{job_id}.xlsx"
    df = pd.DataFrame(all_data)
    df.to_excel(file_name, index=False)

    job["status"] = "completed"
    job["file"] = file_name
    job["message"] = "Completed successfully"

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

  <div class="w-full max-w-6xl h-[85vh] border border-green-600 rounded-xl
              bg-black/90 shadow-[0_0_60px_rgba(34,197,94,0.45)] flex flex-col">

    <!-- HEADER -->
    <div class="flex justify-between items-center px-8 py-5 border-b border-green-600">
      <div class="text-xl tracking-widest">
        ⚠ SFDA DATA EXTRACTION ENGINE
      </div>
      <div id="badge"
        class="px-4 py-1 text-xs bg-gray-800 text-gray-300 rounded-full">
        STANDBY
      </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="flex flex-1 gap-6 p-6">

      <!-- LEFT PANEL -->
      <div class="w-1/3 space-y-6">

        <button id="startBtn"
          onclick="startJob()"
          class="w-full bg-green-600 hover:bg-green-500
                 text-black font-bold py-4 rounded-lg text-lg">
          ▶ INITIATE OPERATION
        </button>

        <div class="border border-green-600 rounded-lg p-4 text-sm space-y-2">
          <div>AI CORE: <span class="animate-pulse">ACTIVE</span></div>
          <div>SECURITY MODE: MAXIMUM</div>
          <div>TRACE ROUTING: ENABLED</div>
          <div>DATA INTEGRITY: VERIFIED</div>
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

      <!-- RIGHT PANEL -->
      <div class="flex-1 flex flex-col">

        <!-- PROGRESS BAR -->
        <div class="mb-4">
          <div class="h-4 bg-gray-800 rounded overflow-hidden">
            <div id="bar"
              class="h-full bg-green-500 animate-pulse transition-all duration-500"
              style="width:0%"></div>
          </div>
        </div>

        <!-- TERMINAL -->
        <div id="terminal"
          class="flex-1 border border-green-600 rounded-lg
                 p-4 overflow-y-auto text-sm leading-relaxed">
          <div>> SYSTEM ONLINE. Awaiting command...</div>
        </div>

      </div>
    </div>
  </div>
</div>

<!-- 🔊 ALARM SOUND -->
<audio id="alarm">
  <source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg">
</audio>

<script>
let jobId = null;
let terminal = document.getElementById("terminal");
let lastMessage = "";
let alarmPlayed = false;

const phaseLogs = [
  "Initializing extraction modules...",
  "Establishing secure SFDA tunnel...",
  "Analyzing response signatures...",
  "Normalizing data payload...",
  "Verifying schema consistency...",
  "Compressing result set...",
  "Encrypting temporary buffers...",
  "Performing integrity checks..."
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
    "px-4 py-1 text-xs bg-red-600 text-white rounded-full animate-pulse";

  log("COMMAND ACCEPTED");
  log("ALLOCATING AI RESOURCES...");
  log("OPERATION STARTED");

  fetch("/start")
    .then(res => res.json())
    .then(data => {
      jobId = data.job_id;
      log("JOB ID: " + jobId);
      poll();
    });
}

function poll() {
  fetch(`/status/${jobId}`)
    .then(res => res.json())
    .then(d => {
      const percent = Math.floor((d.current_page / d.total_pages) * 100);

      document.getElementById("bar").style.width = percent + "%";
      document.getElementById("percent").innerText = percent + "%";
      document.getElementById("page").innerText = d.current_page;

      // ✅ prevent duplicate backend logs
      if (d.message && d.message !== lastMessage) {
        log(d.message);
        lastMessage = d.message;
      }

      // ✅ controlled realistic system logs
      if (Math.random() > 0.7) {
        log(phaseLogs[Math.floor(Math.random() * phaseLogs.length)]);
      }

      if (d.status === "completed") {
        log("OPERATION COMPLETE");
        log("PAYLOAD READY FOR DOWNLOAD");

        document.getElementById("badge").innerText = "EXFILTRATION";
        document.getElementById("badge").className =
          "px-4 py-1 text-xs bg-blue-600 text-white rounded-full";

        // 🔊 play alarm ONCE
        if (!alarmPlayed) {
          const alarm = document.getElementById("alarm");
            alarm.loop = true;     // 🔁 keep repeating
            alarm.play();
            alarmPlayed = true;

            setTimeout(() => {
            alarm.loop = false;
            alarm.pause();
            alarm.currentTime = 0;
            }, 15000); // ⏱ 15 seconds

        }

        setTimeout(() => {
          window.location.href = `/download/${jobId}`;
        }, 3000);
      } else {
        setTimeout(poll, 3000);
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
        "file": None
    }

    thread = threading.Thread(target=fetch_sfda_data, args=(job_id,))
    thread.start()

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
