#!/bin/bash

rm -f *.log
python -m py_compile MyBot.py || exit 1
./halite.exe -d "240 160" "python MyBot.py" "python MyBot0.py"
