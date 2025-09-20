# AUSEC Club Internal Management Tool

[Demo Video](https://youtu.be/Pyn0iIteJAg)  

## Overview
This project is an **internal management tool** designed for the **AUSEC Club** to help manage tasks within the club hierarchy. Each member can assign tasks to their immediate subordinates, track progress, and maintain structured communication.  

The tool is designed for **non-technical users**, providing a simple and clear interface while storing all data in **Google Sheets**, which is easily viewable and manageable.

---

## Website
Access the live application [here](https://ausecclubtoolprototype-ev6g8gmpzf89b6tubwv8rc.streamlit.app).

---

## Problem Statement
- Initially, **Excel** was used as the backend for its familiarity to non-technical users.  
- Issues faced:
  - Data was **stagnant** with no real-time updates.
  - **Data loss** and **connectivity issues**.
- Switching to **Google Sheets API** via **GCP** solved the above problems but introduced **delay issues**, which were later optimized through caching.

---

## Solution
- **Backend Database:** Google Sheets using GCP GSheet API
- **Real-time Updates:** CRUD operations update data instantly.
- **Caching:** Implemented to reduce delays and improve loading times.

---

## Technologies Used
- **Frontend & Deployment:** Streamlit (Python)
- **Backend Database:** Google Sheets via GCP
- **Python Libraries:** gspread, pandas, hashlib
- **Security:** SHA-256 password hashing

---

## Features

### 1. Google Sheets Integration
- Centralized storage for **tasks and members**.
- Secure access using a **Google Service Account**.
- Read/write operations using **gspread**.
- Data caching implemented to reduce repeated API calls.

### 2. User Authentication & Registration
- **Login:**
  - Users log in with name and password.
  - Passwords are **hashed** for security.
  - Only registered users can access the dashboard.
- **Registration:**
  - New users register with name, password, and role.
  - Duplicate usernames are prevented.
  - First registered user recommended as **Core Head** (Admin).

### 3. Role-Based Access Control
- **Roles & Access Levels:**
  - **Core Head:** Full access (view, assign, update, delete tasks)
  - **Domain Head:** Manage tasks for associate heads and below
  - **Associate Head:** Manage tasks for junior heads
  - **Junior Head:** View and update own tasks only
- Ensures structured task delegation and controlled access.

### 4. Task Management System
- **View Tasks:** Color-coded based on status (Not Started, In Progress, Done)
- **Add Task:** Heads can assign tasks with details like Name, Assignee, Priority, Deadline, Description
- **Update Task Status:** Users update their tasks or their subordinates' tasks
- **Delete Task:** Only Core and Domain Heads can delete tasks
- **Completion Description:** Required when marking a task as Done

### 5. Data Caching & Refresh
- Cached for **30 seconds** to enhance performance
- **Manual Refresh:** Button to reload latest data from Google Sheets

### 6. Connection Testing & Error Handling
- **Test Connection:** Button to test Google Sheets connectivity
- **Error Handling:** Friendly messages for connection failures, invalid inputs, and missing data

### 7. User Interface & Experience
- Modern UI with **custom CSS styling**
- Interactive components like metrics, tabs, and forms
- **Help Section:** Expandable guide on the login page for new users

---

## Deployment
- Deployed using **Streamlit**
- Backend is fully handled via **Google Sheets**, making it easy for non-technical users to view all data clearly

---

## How to Use
1. **Access the app:** [Click here](https://ausecclubtoolprototype-ev6g8gmpzf89b6tubwv8rc.streamlit.app)  
2. **Login/Register:** Enter name, password, and role. First user should be Core Head.  
3. **Assign Tasks:** Heads can assign tasks to subordinates.  
4. **Track Tasks:** Tasks are color-coded and status can be updated.  
5. **Refresh Data:** Use the refresh button to see latest updates.  
6. **View Help Section:** Expand help for guidance.

---

## Screenshots

**Main Page**
<img width="2159" height="1238" alt="image" src="https://github.com/user-attachments/assets/6e5d06ce-91b3-4ef2-930e-0c70ac920b93" />
**Developer Dashboard**
<img width="2159" height="1236" alt="image" src="https://github.com/user-attachments/assets/98e31a7a-9982-4fad-a520-5302cfaac0af" />
**Member Dashboard**
<img width="2159" height="1239" alt="image" src="https://github.com/user-attachments/assets/f510af12-7970-4358-aa41-7c08afc04731" />
**Database View 1 (in GSheets)**
<img width="2159" height="1144" alt="image" src="https://github.com/user-attachments/assets/e522a1a7-8b14-440b-bc69-6e94ac58d323" />
**Database View 2 (in Gsheets)**
<img width="2159" height="1155" alt="image" src="https://github.com/user-attachments/assets/f8bae20f-7c39-4b27-b238-0fae3bd202e8" />

---

## Notes for Non-Technical Users
- All task and member data is stored in **Google Sheets**, which can be opened and viewed directly if needed.
- The **hierarchy structure** ensures proper delegation and accountability.
- Real-time updates allow for immediate visibility of changes made by anyone in the club.

---

## Demo Video
Watch the demo [here](https://youtu.be/Pyn0iIteJAg).

---
