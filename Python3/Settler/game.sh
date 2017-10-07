#!/bin/bash

rm -f *.log
python -m py_compile MyBot.py || exit 1
./halite.exe -t -d "240 160" "python MyBot_0.9.1.py" "python MyBot.py" | egrep -v "^Turn"
