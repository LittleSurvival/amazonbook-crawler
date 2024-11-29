import requests
from bs4 import BeautifulSoup
import urllib.parse
import os
import json
import difflib
import re
import math
import time
from tkinter import Tk, Label, Entry, Button, StringVar, END, Text, Scrollbar, RIGHT, Y, BOTH, LEFT, Frame, ttk, X
from tkinter import messagebox
from jinja2 import Environment
import random
import sys
import threading

def generate_config():
    config_file = 'config.json'

    if not os.path.exists(config_file):
        default_config = {
            "baseurl": "https://www.amazon.co.jp"
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config.get("baseurl", "")

def remove_language_parameter(url):
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    # Parse the query parameters into a dict
    query_params = urllib.parse.parse_qs(parsed_url.query)
    # Remove 'language' parameter if it exists
    query_params.pop('language', None)
    # Rebuild the query string
    query_string = urllib.parse.urlencode(query_params, doseq=True)
    # Rebuild the URL without the 'language' parameter
    new_url = urllib.parse.urlunparse(parsed_url._replace(query=query_string))
    return new_url

# List of user agents
user_agents_list = [
    # Add actual user agent strings
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    # Add more user agents as needed
]

def sanitize_filename(name):
    # Remove invalid characters for filenames
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_series_link(base_url, search_input):
    series_link = None

    # Remove 'language' parameter from the input URL if present
    search_input = remove_language_parameter(search_input)

    if search_input.startswith('http'):
        response = requests.get(search_input)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Check if it's already a series link
        series_title = soup.find('span', {'id': 'collection-title'})
        if series_title:
            return search_input  # Input is already a series link

        # Find series link in the page
        anchor_tags = soup.find_all('a', {'class': 'a-link-normal'})

        for anchor in anchor_tags:
            href = anchor.get('href', '')
            if 'dbs_' in href:
                full_link = urllib.parse.urljoin(base_url, href)
                return full_link
        print("No series link found in the provided URL.")
        return None
    else:
        encoded_book_name = urllib.parse.quote(search_input)
        search_url = f"{base_url}/s?k={encoded_book_name}&i=digital-text"

        headers = {"User-Agent": random.choice(user_agents_list)}
        response = requests.get(search_url, headers=headers)
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        search_results = soup.find_all('div', {'data-component-type': 's-search-result'})

        results = []
        for result in search_results:
            data_index = result.get('data-index')
            data_asin = result.get('data-asin')

            image_tag = result.find('img', {'class': 's-image'})
            alt_text = image_tag.get('alt') if image_tag else ''

            anchor_tag = result.find('a', {'class': 'a-link-normal s-underline-text s-underline-link-text s-link-style'})
            href = anchor_tag.get('href') if anchor_tag else ''
            full_link = urllib.parse.urljoin(base_url, href) if href else ''

            results.append({
                'data_index': data_index,
                'data_asin': data_asin,
                'alt_text': alt_text,
                'series_link': full_link
            })

        # Remove items where the series link is empty
        results = [item for item in results if item['series_link']]

        # Use difflib to find the best match based on word-level similarity
        best_match = None
        highest_similarity = 0

        # Assign similarity score to each item
        for item in results:
            # Split the alt_text into words
            alt_words = item['alt_text'].split()
            search_words = search_input.split()

            # Calculate similarity based on word sets
            similarity = difflib.SequenceMatcher(None, ' '.join(search_words), ' '.join(alt_words)).ratio()
            item['similarity'] = similarity

        # Now, sort the results based on similarity
        results_with_similarity = sorted(results, key=lambda x: x['similarity'], reverse=True)

        if results_with_similarity:
            # Handle items with close similarity scores
            top_similarity = results_with_similarity[0]['similarity']
            top_items = [item for item in results_with_similarity if abs(item['similarity'] - top_similarity) < 0.2]
            preferred_item = None

            for item in top_items:
                if '文庫' in item['alt_text']:
                    preferred_item = item
                    break
            if not preferred_item:
                preferred_item = results_with_similarity[0]

            best_match = preferred_item
            highest_similarity = best_match['similarity']

        else:
            best_match = None
            highest_similarity = 0

        if best_match and highest_similarity > 0.3:
            series_link = best_match['series_link']
            print(f"Best match similarity: {highest_similarity * 100:.2f}%")
            return series_link
        else:
            print("No matching series link found.")
            return None

def get_series_info(series_url, base_url):
    series_url = remove_language_parameter(series_url)
    print("Collecting page 1 info...")
    response = requests.get(series_url)
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')

    # Get series image
    image_tag = soup.find('img', {'id': 'seriesImageBlock'})
    series_image = image_tag.get('src') if image_tag else ''

    # Get series title
    title_tag = soup.find('span', {'id': 'collection-title'})
    series_title = title_tag.text.strip() if title_tag else ''

    # Get series description
    description_tag = soup.find('span', {'id': 'collection_description'})
    series_description = description_tag.get_text(separator='\n').strip() if description_tag else ''

    # Initialize authors and illustrators lists
    authors = []
    illustrators = []

    # Find all contributor spans
    contributor_spans = soup.find_all('span', {'class': 'a-declarative', 'data-action': 'a-popover'})

    for contributor_span in contributor_spans:
        # Get the text content
        text = str(contributor_span)

        # If the text doesn't contain "Author" or "著" or "Illustrator" or "イラスト", skip it
        if not ("Author" in text or "著" in text or "Illustrator" in text or "イラスト" in text):
            continue

        # For authors
        if "Author" in text or "著" in text:
            # Find the text between the start and "(Author)" or "（著）"
            if "(Author)" in text:
                name = text.split("(Author)")[0].split("\\r\\n")[-1].strip()
                authors.append(name)
            elif "（著）" in text:
                name = text.split("（著）")[0].split("\\r\\n")[-1].strip()
                authors.append(name)

        # For illustrators
        if "Illustrator" in text or "イラスト" in text:
            if "(Illustrator)" in text:
                name = text.split("(Illustrator)")[0].split("\\r\\n")[-1].strip()
                illustrators.append(name)
            elif "（イラスト）" in text:
                name = text.split("（イラスト）")[0].split("\\r\\n")[-1].strip()
                illustrators.append(name)

    # Remove duplicates
    authors = list(set(authors))
    illustrators = list(set(illustrators))

    # Get books in the series from the first page (HTML parsing)
    books = []
    for a_tag in soup.find_all('a', {'id': re.compile(r'itemBookTitle_\d+')}):
        href = a_tag.get('href', '')
        asin_match = re.search(r'/gp/product/(\w{10})', href)
        if asin_match:
            asin = asin_match.group(1)
            books.append(asin)

    # Get total number of books in the series
    collection_size_tag = soup.find('span', {'id': 'collection-size'})
    total_books = 0
    if collection_size_tag:
        size_text = collection_size_tag.text.strip()
        match = re.search(r'\d+', size_text)
        if match:
            total_books = int(match.group())
    else:
        print("Unable to determine the total number of books in the series.")

    if total_books > 10:
        # Calculate the total number of pages
        total_pages = math.ceil(total_books / 10)
        print(f"Total pages: {total_pages}")

        # Fetch additional pages (from page 2 onwards)
        for page_number in range(2, total_pages + 1):
            print(f"Collecting page {page_number}...")
            # Pause to queue the website loading
            time.sleep(1)
            # Construct the URL for the next page
            parsed_url = urllib.parse.urlparse(series_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            query_params['pageNumber'] = [str(page_number)]
            query_string = urllib.parse.urlencode(query_params, doseq=True)
            page_url = urllib.parse.urlunparse(parsed_url._replace(query=query_string))
            page_url = remove_language_parameter(page_url)

            response = requests.get(page_url)
            if response.status_code == 200:
                page_html = response.text
                page_soup = BeautifulSoup(page_html, 'html.parser')
                for a_tag in page_soup.find_all('a', {'id': re.compile(r'itemBookTitle_\d+')}):
                    href = a_tag.get('href', '')
                    asin_match = re.search(r'/gp/product/(\w{10})', href)
                    if asin_match:
                        asin = asin_match.group(1)
                        books.append(asin)
            else:
                print(f"Failed to fetch page {page_number}. Status code: {response.status_code}")
    else:
        print("Only one page of results found.")

    # Remove duplicates
    books = list(dict.fromkeys(books))

    series_info = {
        'Series Title': series_title,
        'Series Image URL': series_image,
        'Series Description': series_description,
        'Authors': authors,
        'Illustrators': illustrators,
        'Books ASINs': books
    }

    return series_info

def get_books_info(base_url, asin, headers=None):
    book_urls = [
        f"{base_url}/dp/{asin}",
        f"{base_url}/zh/dp/{asin}"
    ]

    book_info = None
    last_exception = None
    response = None  # Initialize response

    for url in book_urls:
        url = remove_language_parameter(url)
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Received status code {response.status_code} for URL {url}")
                continue
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            # Initialize book_info dictionary
            book_info = {}

            # 0. Get book title
            title_tag = soup.find('span', {'id': 'productTitle'})
            book_title = title_tag.text.strip() if title_tag else ''
            book_info['Title'] = book_title

            # 1. Get thumbnail image link
            thumbnail_tag = soup.find('img', {'id': 'landingImage'})
            if thumbnail_tag:
                thumbnail = thumbnail_tag.get('src', '')
                # Remove size specifier to get the largest image
                thumbnail = re.sub(r'\._[A-Z0-9,]+_\.', '.', thumbnail)
                book_info['thumbnail'] = thumbnail

            # 2. Get large image link
            if thumbnail_tag:
                data_dynamic_image = thumbnail_tag.get('data-a-dynamic-image', '')
                if data_dynamic_image:
                    try:
                        images_dict = json.loads(data_dynamic_image)
                        # Assuming the largest image has the highest resolution
                        large_image = max(images_dict.keys(), key=lambda x: images_dict[x][0]*images_dict[x][1])
                        # Remove size specifier from large image URL
                        large_image = re.sub(r'\._[^_]+_', '', large_image)
                        book_info['largeImage'] = large_image
                    except json.JSONDecodeError:
                        book_info['largeImage'] = ''
                else:
                    # Fallback if data-a-dynamic-image is not available
                    large_image_tag = soup.find('img', {'class': 'fullscreen'})
                    large_image = large_image_tag.get('src', '') if large_image_tag else ''
                    # Remove size specifier from large image URL
                    large_image = re.sub(r'\._[^_]+_', '', large_image)
                    book_info['largeImage'] = large_image
            else:
                book_info['largeImage'] = ''


            # 3. Get Description as a dictionary
            description_dict = {}
            detail_bullets = soup.find('div', {'id': 'detailBullets_feature_div'})
            if detail_bullets:
                # Extract all list items
                for li in detail_bullets.find_all('li'):
                    spans = li.find_all('span', {'class': 'a-list-item'})
                    for s in spans:
                        text = s.get_text(separator=' ', strip=True)
                        # Remove unnecessary whitespaces and colons
                        text = re.sub(r'\s+', ' ', text)
                        text = text.replace('‎', '').replace('‏', '').strip()
                        if ':' in text:
                            key_value = text.split(':', 1)
                            key = key_value[0].strip()
                            value = key_value[1].strip()
                            description_dict[key] = value
                        else:
                            # Handle cases where key and value are not separated by colon
                            parts = text.split()
                            if len(parts) >= 2:
                                key = parts[0].strip()
                                value = ' '.join(parts[1:]).strip()
                                description_dict[key] = value
            book_info['Description'] = description_dict

            # 4. Get authors and illustrators
            authors = []
            illustrators = []

            byline_info = soup.find('div', {'id': 'bylineInfo'})
            if byline_info:
                contributors = byline_info.find_all('span', {'class': 'author'})
                for contributor in contributors:
                    name_tag = contributor.find('a', {'class': 'a-link-normal'})
                    role_tag = contributor.find('span', {'class': 'contribution'})
                    if name_tag and role_tag:
                        name = name_tag.get_text(strip=True)
                        role_text = role_tag.get_text(strip=True)
                        if '(著)' in role_text or 'Author' in role_text:
                            authors.append(name)
                        elif '(イラスト)' in role_text or 'Illustrator' in role_text:
                            illustrators.append(name)
                        else:
                            # Default to authors if role is unspecified
                            authors.append(name)

            # Remove duplicates
            authors = list(set(authors))
            illustrators = list(set(illustrators))

            # 5. Get preface (if any)
            preface = ''
            # Assuming the preface is in a <span> with no id or class
            book_description_div = soup.find('div', {'id': 'bookDescription_feature_div'})
            if book_description_div:
                spans = book_description_div.find_all('span')
                for span in spans:
                    # Exclude spans with id or class
                    if not span.get('id') and not span.get('class'):
                        preface = span.get_text(separator='\n').strip()
                        break  # Assuming the first such span is the preface
            book_info['Preface'] = preface

            book_info['Authors'] = authors
            book_info['Illustrators'] = illustrators
            book_info['ASIN'] = asin  # Add ASIN to book_info

            # Book info successfully retrieved
            return book_info

        except requests.exceptions.RequestException as e:
            last_exception = e
            print(f"Request exception for URL {url}: {e}")
            continue
        except Exception as e:
            last_exception = e
            print(f"An error occurred while processing URL {url}: {e}")
            continue

    # If all attempts fail, provide detailed error info
    print(f"Failed to retrieve book info for ASIN {asin}. Last error: {last_exception}")
    # Print the response content if available
    if response:
        print(f"Response content for ASIN {asin}:\n{response.text}")
    return None

def print_series_info(series_info):
    print("\nSeries Information:")
    print("-------------------")
    print(f"Series Title: {series_info.get('Series Title', 'N/A')}")
    print(f"Series Image URL: {series_info.get('Series Image URL', 'N/A')}")
    print(f"Series Description: {series_info.get('Series Description', 'N/A')}")
    print("\nAuthors:")
    for author in series_info.get('Authors', []):
        print(f" - {author}")
    print("\nIllustrators:")
    for illustrator in series_info.get('Illustrators', []):
        print(f" - {illustrator}")
    print("\nBooks ASINs:")
    for asin in series_info.get('Books ASINs', []):
        print(f" - {asin}")

def print_book_info(book_info):
    print("\nBook Information:")
    print("-----------------")
    print(f"Title: {book_info.get('Title', 'N/A')}")
    print(f"Thumbnail: {book_info.get('thumbnail', 'N/A')}")
    print(f"Large Image: {book_info.get('largeImage', 'N/A')}")
    print("\nDescription:")
    for key, value in book_info.get('Description', {}).items():
        print(f" - {key}: {value}")
    print("\nAuthors:")
    for author in book_info.get('Authors', []):
        print(f" - {author}")
    print("\nIllustrators:")
    for illustrator in book_info.get('Illustrators', []):
        print(f" - {illustrator}")
    print("\nPreface:")
    print(book_info.get('Preface', 'N/A'))
    print("\n\n")  # Added two newlines at the end

def export_to_html(series_info, books_info_list, base_url, single_book=False):
    # Ensure the /output directory exists
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Determine the filename
    if single_book:
        if books_info_list and books_info_list[0]:
            title = books_info_list[0].get('Title', 'book_info')
        else:
            title = 'book_info'
    else:
        title = series_info.get('Series Title', 'series_info')

    sanitized_title = sanitize_filename(title)
    filename = f"{sanitized_title}.html"
    file_path = os.path.join(output_dir, filename)

    # Use Jinja2 template for HTML export
    env = Environment()
    template_string = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ series['Series Title'] if not single_book else books[0]['Title'] }}</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            img { max-width: 200px; }
            .book { border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; }
            h1, h2, h3 { color: #333; }
            a { color: #1a0dab; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        {% if not single_book %}
        <h1>{{ series['Series Title'] }}</h1>
        <img src="{{ series['Series Image URL'] }}" alt="{{ series['Series Title'] }}">
        <p>{{ series['Series Description'] | nl2br }}</p>
        <h2>Authors</h2>
        <ul>
            {% for author in series['Authors'] %}
            <li>{{ author }}</li>
            {% endfor %}
        </ul>
        <h2>Illustrators</h2>
        <ul>
            {% for illustrator in series['Illustrators'] %}
            <li>{{ illustrator }}</li>
            {% endfor %}
        </ul>
        {% endif %}
        <h2>{{ 'Book' if single_book else 'Books' }}</h2>
        {% for book in books %}
        <div class="book">
            <h3><a href="{{ base_url }}/dp/{{ book['ASIN'] }}" target="_blank">{{ book['Title'] }}</a></h3>
            <img src="{{ book['thumbnail'] }}" alt="{{ book['Title'] }}">
            <p><strong>Authors:</strong> {{ ', '.join(book['Authors']) }}</p>
            <p><strong>Illustrators:</strong> {{ ', '.join(book['Illustrators']) }}</p>
            <p><strong>Description:</strong></p>
            <ul>
                {% for key, value in book['Description'].items() %}
                <li>{{ key }}: {{ value }}</li>
                {% endfor %}
            </ul>
            <p><strong>Preface:</strong><br>{{ book['Preface'] | nl2br }}</p>
            <p><strong>Large Image:</strong> <a href="{{ book['largeImage'] }}" target="_blank">{{ book['largeImage'] }}</a></p>
        </div>
        {% endfor %}
    </body>
    </html>
    """
    env.filters['nl2br'] = lambda text: text.replace('\n', '<br>') if text else ''
    template = env.from_string(template_string)

    # Filter out None entries in books_info_list
    valid_books_info = [book for book in books_info_list if book]

    rendered_html = template.render(series=series_info, books=valid_books_info, base_url=base_url, single_book=single_book)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    print(f"Exported data to {file_path}")

class RedirectText(object):
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        def append():
            self.text_widget.insert(END, string)
            self.text_widget.see(END)
        self.text_widget.after(0, append)

    def flush(self):
        pass

def run_application(search_input, log_text_widget, progress_bar, submit_button, redirect_text):
    # Set sys.stdout to redirect_text inside the thread
    sys.stdout = redirect_text

    base_url = generate_config()
    series_link = get_series_link(base_url, search_input)
    if series_link:
        series_info = get_series_info(series_link, base_url)
        if series_info.get('Books ASINs'):
            print_series_info(series_info)
            books_info_list = [None] * len(series_info.get('Books ASINs', []))
            failed_indices = []
            retry_counts = {}
            max_retries = 5  # Increased max retries to 5
            delay = 1  # Initial delay in seconds

            total_books = len(series_info.get('Books ASINs', []))
            completed_books = 0

            # Update progress bar maximum
            progress_bar['maximum'] = total_books

            # First attempt
            for idx, asin in enumerate(series_info.get('Books ASINs', [])):
                if not submit_button.running:
                    print("Process stopped by user.")
                    break
                time.sleep(delay)  # Add delay before running get_books_info
                headers = {"User-Agent": random.choice(user_agents_list)}
                book_info = get_books_info(base_url, asin, headers=headers)
                # Check if critical fields are empty
                critical_fields = ['Authors', 'Illustrators', 'Description', 'Preface']
                is_incomplete = any(not book_info.get(field) for field in critical_fields) if book_info else True
                if book_info and not is_incomplete:
                    books_info_list[idx] = book_info
                    print_book_info(book_info)
                else:
                    failed_indices.append(idx)
                    retry_counts[asin] = 1
                    if is_incomplete:
                        print(f"Book info incomplete for ASIN {asin}. Missing critical fields. Will retry later.")
                    else:
                        print(f"Failed to get info for ASIN {asin}. Will retry later.")
                completed_books += 1
                progress_bar['value'] = completed_books
                progress_bar.update()

            # Retry loop with adaptive delay and random user-agent
            while failed_indices and submit_button.running:
                print("Retrying failed ASINs...")
                time.sleep(delay)  # Delay before starting retries
                new_failed_indices = []
                for idx in failed_indices:
                    if not submit_button.running:
                        print("Process stopped by user.")
                        break
                    asin = series_info['Books ASINs'][idx]
                    retries = retry_counts.get(asin, 1)
                    if retries >= max_retries:
                        print(f"Max retries reached for ASIN {asin}. Skipping.")
                        continue
                    time.sleep(delay)  # Add delay before retry
                    headers = {"User-Agent": random.choice(user_agents_list)}
                    book_info = get_books_info(base_url, asin, headers=headers)
                    # Check if critical fields are empty
                    critical_fields = ['Authors', 'Illustrators', 'Description', 'Preface']
                    is_incomplete = any(not book_info.get(field) for field in critical_fields) if book_info else True
                    if book_info and not is_incomplete:
                        books_info_list[idx] = book_info
                        print_book_info(book_info)
                        print(f"Successfully retrieved info for ASIN {asin} on retry {retries}.")
                        completed_books += 1
                        progress_bar['value'] = completed_books
                        progress_bar.update()
                    else:
                        new_failed_indices.append(idx)
                        retry_counts[asin] = retries + 1
                        if is_incomplete:
                            print(f"Retry {retries} failed for ASIN {asin}. Book info incomplete. Will retry again later.")
                        else:
                            print(f"Retry {retries} failed for ASIN {asin}. Will retry again later.")
                if new_failed_indices == failed_indices:
                    # No progress made, increase delay to prevent rate limiting
                    delay *= 2
                    print(f"No progress made. Increasing delay to {delay} seconds.")
                else:
                    # Reset delay if progress is made
                    delay = 1
                failed_indices = new_failed_indices

            # Log any ASINs that could not be retrieved after retries
            for idx in failed_indices:
                asin = series_info['Books ASINs'][idx]
                print(f"Failed to retrieve complete info for ASIN {asin} after {max_retries} retries.")

            # Export all collected data to an HTML file
            export_to_html(series_info, books_info_list, base_url, single_book=False)
            print("Exported data to HTML.")
            submit_button.config(text="Submit")

            # Notify user
            messagebox.showinfo("Export Complete", "Exported data to the /output folder.")
        else:
            # If no books found in series, treat it as a single book
            print("No books found in series. Treating as single book.")
            asin = series_link.split('/dp/')[1].split('/')[0]
            headers = {"User-Agent": random.choice(user_agents_list)}
            book_info = get_books_info(base_url, asin, headers=headers)
            if book_info:
                print_book_info(book_info)
                export_to_html({}, [book_info], base_url, single_book=True)
                print("Exported single book data to HTML.")
                messagebox.showinfo("Export Complete", "Exported data to the /output folder.")
            else:
                print(f"Failed to retrieve book info for ASIN {asin}.")
    
    submit_button.config(text="Submit")

def start_gui():
    root = Tk()
    root.title("Series Info Collector")
    root.geometry("800x600")  # Increased default size

    frame = Frame(root)
    frame.pack(padx=10, pady=10)

    label = Label(frame, text="Enter the book name or URL:")
    label.grid(row=0, column=0, padx=5, pady=5)

    input_var = StringVar()
    entry = Entry(frame, textvariable=input_var, width=50)
    entry.grid(row=0, column=1, padx=5, pady=5)

    # Log Text Widget
    log_text = Text(root, wrap='word', height=20)
    log_text.pack(fill=BOTH, expand=True)

    # Add scrollbar to the log text
    scrollbar = Scrollbar(log_text, command=log_text.yview)
    scrollbar.pack(side=RIGHT, fill=Y)
    log_text['yscrollcommand'] = scrollbar.set

    # Progress Bar
    progress_bar = ttk.Progressbar(root, orient='horizontal', mode='determinate')
    progress_bar.pack(fill=X, padx=10, pady=10)

    def on_submit():
        if not hasattr(on_submit, "thread") or not on_submit.thread.is_alive():
            search_input = input_var.get()
            if not search_input:
                messagebox.showwarning("Input Required", "Please enter a book name or URL.")
                return

            # Clear previous logs
            log_text.delete(1.0, END)

            # Redirect stdout to the log_text widget
            redirect_text = RedirectText(log_text)

            # Change button text to "Stop"
            submit_button.config(text="Stop")
            submit_button.running = True

            # Run the application in a separate thread to avoid freezing the GUI
            on_submit.thread = threading.Thread(target=run_application, args=(search_input, log_text, progress_bar, submit_button, redirect_text), daemon=True)
            on_submit.thread.start()
        else:
            # Stop the running process
            submit_button.running = False
            submit_button.config(text="Submit")
            print("Stopping process...")

    submit_button = Button(frame, text="Submit", command=on_submit)
    submit_button.grid(row=1, column=0, columnspan=2, pady=5)
    submit_button.running = False  # Custom attribute to track running state

    root.mainloop()

if __name__ == "__main__":
    start_gui()