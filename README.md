Score Tracker

A simple CLI tool to track daily game wins and analyze statistical significance.

Installation

Ensure you have uv installed, then run this in the project folder:

uv tool install .


Usage

Add a win for today:

geohunter-tally --add James


Add a win if someone was absent:

geohunter-tally --add James --absent Magnus


View current standings:

geohunter-tally
