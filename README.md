# tinkertown-transit-reimbursements
Script to automate the transit reimbursement process on Benepass.

0. Place combined .pdf into a folder in transit directory
1. Run `python3 pdf_burst.py transit/<new_folder>/<filename.pdf>`
2. Run `python3 auth.py` to authenticate into Benepass and store session .json into transit directory
3. Run `python3 uploader.py transit/<new_folder>/burst` to begin processing all files in that folder

Script will run until the following:
    - Amount in the file exceeds available balance
    - All files are processed

Files will be sorted into processed and failed folders as appropriate. Those files that have not been processed 
will remain in the root directory.

---------

Future improvements:
- Combine pdf_brust, uploader and auth into one script
- Document the code and understand what's going one
- Export audit logs into a text file in the main directory
- Build interactive elements when you run the script in terminal