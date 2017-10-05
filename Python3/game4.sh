#!/bin/bash

rm -f *.log
python -m py_compile MyBot.py || exit 1
./halite.exe -t -d "384 256" "python MyBot.py" "python MyBot0.py" "python MyBot1.py" "python MyBot2.py"
