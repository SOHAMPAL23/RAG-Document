$frontend = Start-Process -NoNewWindow -PassThru powershell -ArgumentList "-Command", "cd frontend; npm run dev"
$backend = Start-Process -NoNewWindow -PassThru powershell -ArgumentList "-Command", "cd backend; .\venv\Scripts\activate; uvicorn main:app --reload --port 8000"

Write-Host "Both servers are starting... "
Wait-Process -Id $frontend.Id, $backend.Id
