# How Riverbend Votes counts doors, attempts and contacts

## Doors
A door is one address unit (a house, or one apartment unit) knocked on one day. Our dashboard counts each door once per day no matter how many times it was knocked that day. Doors knocked on different days count again on each day, so a second pass on a not-home door adds a door on the day of the second pass.

## Attempts
An attempt is every knock record the canvassing app submits. If a canvasser knocks a not-home door at 11:00 and comes back at 14:00, that is two attempts and one door. Attempts are always equal to or higher than doors.

## Contacts and contact rate
A contact is a knock with the result "canvassed", meaning the canvasser spoke with the voter. Not home, refused and inaccessible are not contacts. Contact rate is contacts divided by doors for the same period and office.

## Rollbacks
When QC confirms flash knocking, the knocks in the flagged window are rolled back: they stay in the data with rolled_back = true but are removed from doors and contacts. Rollbacks happen after the day's client report has been pulled, so they never change a report that was already sent.

## Why the client's numbers differ from ours
The client daily report counts attempts, pulled at the end of each day before any QC rollback. Our dashboard counts doors with rollbacks removed. The gap on any day is the repeat attempts at the same door plus any attempts that were later rolled back. A normal day shows a gap of a few percent from repeat attempts. A larger gap almost always means a rollback.
