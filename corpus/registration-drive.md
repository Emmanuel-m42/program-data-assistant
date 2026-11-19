# Riverbend Registers voter registration drive

## Overview
Riverbend Registers is a paid voter registration drive run from the same three offices, Northside, Eastgate and Harbor, with its own registration canvassers. Collection started September 21, 2026 and ends at the registration deadline, Friday, October 30, 2026. Each office has a card goal in the registration goals table.

## Valid cards and duplicates
A card is one completed registration form. A duplicate is a second card for a registrant who already has a card in the drive; duplicates share a duplicate group id with the first card and are marked is_duplicate. Only valid cards (duplicates removed) count toward goal and cards per hour. A canvasser with a duplicate rate above 10 percent gets a retraining conversation.

## Cards per hour
Cards per hour is valid cards divided by paid registration hours. Current pace uses the last 7 days. The cards per hour needed from here is the cards still needed (goal minus valid cards) divided by the hours we expect to work before the deadline: average daily registration hours of the last 7 days times days left. An office is under the needed rate when its last 7 days rate is below the program-wide rate needed.

## QC calls
A sample of valid cards gets a QC call a day or two after collection. Outcomes are confirmed (the registrant confirms they filled out the card), unreachable (no answer after two tries) and wrong_info (the person says the details are wrong or they did not register). Wrong information above 10 percent of calls for a canvasser is escalated.
