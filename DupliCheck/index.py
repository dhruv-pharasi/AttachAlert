from flask import Flask, render_template, request, jsonify
from pyspark.sql import SparkSession
from PIL import Image
import imagehash
import io
import os
import sys
import base64
import pandas as pd
import matplotlib.pyplot as plt
import time
import datetime
from os import listdir

delete_button_clicks = []
deletion_timestamps = []


def runSparkjob(file_loc):
    os.environ['PYSPARK_PYTHON'] = sys.executable
    os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

    # Create a SparkSession
    spark = SparkSession.builder \
        .master("local[*]") \
        .appName("ImageHashing") \
        .getOrCreate()
    
    start_time_parallelize = time.time()

    # Define a function to compute image hash
    def compute_image_hash(image_data):
        image = Image.open(io.BytesIO(image_data))
        return str(imagehash.average_hash(image))

    # Read images into RDD
    image_rdd = spark.sparkContext.binaryFiles(file_loc + "/*.png")

    # Map the image RDD to compute hashes
    hash_rdd = image_rdd.map(lambda x: (x[0], compute_image_hash(x[1])))

    distance_rdd = hash_rdd.cartesian(hash_rdd).map(lambda x : (x[0][0], x[1][0], abs(imagehash.hex_to_hash(x[0][1]) - imagehash.hex_to_hash(x[1][1]))))

    similarity_rdd = distance_rdd.filter(lambda x : x[2] <= 10 and x[2] != 0)

    # Convert RDD to DataFrame
    similarity_df = similarity_rdd.toDF(["path1", "path2", "similarity"])

    print("Time taken to do task with parallelization :", time.time() - start_time_parallelize, "seconds")

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    csv_filename = f"output_path/run_{timestamp}.csv"

    # For example, you can save the DataFrame to a file
    similarity_df.write.mode("overwrite").csv(csv_filename)

    # Stop the SparkSession
    spark.stop()

# Function to sort values in the first two columns and join them
def sort_and_join(row):
    sorted_values = sorted(row.iloc[:2])
    return ','.join(sorted_values)

def plot_graph():
    # Get all directories within output_path
    directories = [os.path.join("output_path", d) for d in os.listdir("output_path") if os.path.isdir(os.path.join("output_path", d))]

    # Sort directories by modification time
    sorted_directories = sorted(directories, key=lambda d: os.path.getmtime(d), reverse=False)

    num_runs = len(sorted_directories)

    duplicate_counts = []

    # Iterate over directories
    for directory in sorted_directories:
        # Number of duplicate files at each run
        csv_files = [directory + "/" + file for file in os.listdir(directory) if file.endswith('.csv')]

        duplicate_counts.append(len(pd.read_csv(csv_files[0], header = None)) // 2)

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(range(1, num_runs + 1), duplicate_counts, marker='o', linestyle='-')
    plt.title('Number of Duplicate Files Over Time')
    plt.xlabel('Run Number')
    plt.ylabel('Number of Duplicate Files')
    plt.grid(True)
    plt.savefig('static/duplicate_files_over_time.png')  # Save the plot as an image with directory name
    plt.close()  # Close the plot to release memory

    plt.figure(figsize=(10, 6))
    plt.plot(deletion_timestamps, delete_button_clicks, marker='o')
    plt.xlabel('Time')
    plt.ylabel('Milligrams of CO2 Saved (Approx.)')
    plt.title('CO2 Emmissions saved')
    plt.grid(True)
    plt.xticks(rotation=45)  # Rotate x-axis labels for better readability
    plt.tight_layout()  # Adjust layout to prevent overlapping labels
    plt.savefig('static/delete_button_clicks_over_time.png')  # Save the graph image
    plt.close()

    



def get_latest_modified_subdirectory(directory):
    # Get a list of all items (files and directories) within the directory
    all_items = [os.path.join(directory, item) for item in os.listdir(directory)]

    # Filter out directories
    subdirectories = [item for item in all_items if os.path.isdir(item)]

    # Get modification timestamps for each subdirectory
    timestamps = [(subdir, os.path.getmtime(subdir)) for subdir in subdirectories]

    # Find the subdirectory with the latest modification timestamp
    latest_subdirectory = max(timestamps, key=lambda x: x[1], default=None)

    return latest_subdirectory[0] if latest_subdirectory else None 


app = Flask(__name__)

@app.route('/')
def index():
    plot_graph()
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    text = request.form['text']
    runSparkjob(text)

    directory_path = "output_path"
    latest_subdirectory = get_latest_modified_subdirectory(directory_path)

    csv_files = [file for file in listdir(latest_subdirectory) if file.endswith('.csv')]

    df = pd.read_csv(latest_subdirectory + '/' + csv_files[0], header=None)

    # Apply the function to each row to create a new column
    df['Sorted'] = df.apply(sort_and_join, axis=1)

    # Drop duplicates based on the sorted values
    df = df.drop_duplicates(subset='Sorted')

    # Drop the additional 'Sorted' column
    df = df.drop(columns=['Sorted'])

    print(df.iloc[:,0].values.tolist())

    image_data = {}


    for index, (image1_name, image2_name) in enumerate(zip(df.iloc[:,0].values.tolist(), df.iloc[:,1].values.tolist())):
        image1_name = image1_name.replace("file:","")
        image2_name = image2_name.replace("file:","")
        with open(image1_name, 'rb') as f1:
            img1_data = f1.read()
            img1_base64 = base64.b64encode(img1_data).decode('utf-8')
            with open(image2_name, 'rb') as f2:
                img2_data = f2.read()
                img2_base64 = base64.b64encode(img2_data).decode('utf-8')
                image_data[index] = (img1_base64, img2_base64, image1_name, image2_name)

    return render_template('resp.html', image_data=image_data)

@app.route('/delete_image', methods=['POST'])
def delete_image():
    # Get the image name from the request data
    image_name = request.json.get('imageName')

    # Check if the file exists and delete it
    if os.path.exists(image_name):
        os.remove(image_name)

        delete_button_clicks.append(5 * (len(delete_button_clicks) + 1))
        deletion_timestamps.append(datetime.datetime.now())

        return jsonify({'message': 'Image deleted successfully'}), 200
    else:
        return jsonify({'message': 'Image not found'}), 404

if __name__ == '__main__':
    app.run()
 
