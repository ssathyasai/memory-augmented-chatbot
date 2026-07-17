#!/bin/bash
export PYTHONPATH=/opt/render/project/src:$PYTHONPATH
cd backend
uvicorn main:app --host 0.0.0.0 --port $PORT
