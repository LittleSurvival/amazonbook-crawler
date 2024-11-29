# Series Info Collector

This project is a tool to extract information about books and series from websites such as Amazon. The following steps will guide you through setting up and using the tool.

## Installation and Setup

1. **Install Python**
   
   Make sure Python (version 3.10 or newer) is installed on your system. You can download it from [https://www.python.org/downloads/](https://www.python.org/downloads/). Always ensure you are using the latest version of Python for compatibility and performance improvements.

2. **Set Up Virtual Environment**
   
   Create a virtual environment to manage project dependencies. Run the following commands in your terminal:
   ```sh
   python -m venv venv
   ```

3. **Activate Virtual Environment**
   
   - On Windows:
     ```sh
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```sh
     source venv/bin/activate
     ```

4. **Install Dependencies**
   
   Double-click `setup.bat` or run the following command to install all the necessary Python libraries from `requirements.txt`:
   ```sh
   pip install -r requirements.txt
   ```

5. **Configure the Base URL**
   
   Update the `config.json` file with the base URL of the target site. For example:
   ```json
   {
       "baseurl": "http://www.amazon.co.jp/"
   }
   ```

6. **Launch the Application**
   
   Run `launch.bat` to start the application. Make sure your virtual environment is activated before launching. This will open a GUI window:

   ![GUI Window](img/gui.png)

## Usage

- The GUI allows you to search for books using their name, a direct book link, or a series link.
- Once a search is performed, the information is displayed in the GUI:

  ![Running Application](img/running.png)

7. **Extract and Save HTML Output**
   
   After extraction, the data is saved in HTML format in the `/output` directory. The output format is displayed below:

   ![HTML Output](img/result.png)

## TODO

- Implement an auto-correction feature (using a language model or AI crawler) to prevent issues when the website source changes.
- Add functionality to grab books that belong to a series but do not have a dedicated series page.
- Enable extraction of R18 novels (this will require a Japanese IP and bypassing age verification).
