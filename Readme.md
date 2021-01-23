## Ad Parser

#### About
___

This is a project for my friend working as an online advertising specialist. Big part of his day-to-day routine is dedicated to collecting advertising campaign deliverables and copying them to team's Google Spreadsheet.

I suggested to develop an app for him to automate this process. Python is well suited for parsing web resources and workflow automation in general (as I heard), so I chose it as an app language. I also wanted to practice it :)

As a result this application even in the current version (I focused efforts on parsing the most loaded ad platfroms) saves approx. 50% of time my friend spent on this routine.

#### App Workflow
___

On app launch a GUI is shown as a way to collect user input.

In the app menu:

1. User sets up Google Speadsheet: enters its id, chooses sheet with aggregated ad campaign data and column names corresponding to each deliverable.
2. Then user chooses platforms.
3. He also may read current app limitations and assumptions, made by the developer (me).

Then the main window displays fields to be filled by user:

1. Add button on press creates a row to insert campaing id (together with a client id in some platforms), what deliverables to collect (these are money spent, impressions, number of clicks, audience reach), period and delete button.
2. After filling out all the necessary forms user may save current work by pressing the save button or launch the main process (which also saves config for future launches).
3. In the end user receives a short report on the work done.

#### Problems solved 
___

1. **Authorization.** This was the most difficult problem for me. All data is password protected and belongs to agency account, so it was crutial to make sure all the work is done on behalf of this particular user, just in automated fashion. The answer was found in the use of API (VK) and browser cookies.
2. **User input.** It is quite large given that there are >5 campaings monitored at the same time. Besides my friend is not used to CLI. So GUI became necessary. I chose Tkinter as it is lightweight, simple, built-in and cross-platform (friend uses MacOS and I am developing under Windows)
3. **Design questions.** I had to make and change decisions about how to organise code for the simplicity and ease of maintenance. That's why I had to rewrite major parts 3-4 times.