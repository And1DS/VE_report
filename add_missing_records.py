import json, re, time
from algoliasearch.configs import SearchConfig
from algoliasearch.search_client import SearchClient
from algoliasearch.exceptions import RequestException
from algoliasearch.exceptions import AlgoliaUnreachableHostException



def init_algolia_client(appId, apiKey, batch_size=500):
    # Initialize the Algolia client
    config = SearchConfig(appId, apiKey)
    config.batch_size = batch_size

    client = SearchClient.create_with_config(config)
    return client

def send_data_to_algolia(client, data, index_name, counter, exceeded_records):
    
    print(f"Sending data to Algolia: index {index_name} # records {len(data)}")
    index = client.init_index(index_name)
    try: 
        res = index.save_objects(data)
    except RequestException as e:
        if 'is too big' in str(e):
            print(f"Record too big: {e}")
            for record in data:
                try:
                    index.save_object(record)
                except RequestException as inner_e:
                    print("Error saving individual record:", inner_e)
                    exceeded_records.append(record)
        else:
            print("An unexpected error occurred:", e)
            
    except AlgoliaUnreachableHostException as ue:
        print("Algolia is unreachable, waiting 20 seconds:", ue)
        time.sleep(20)
        cnt, exc = send_data_to_algolia(client, data, index_name, counter, exceeded_records)
        return (cnt, exc)



INPUT_FILE = input('Enter the path to the input file: ')
OUTPUT_FILE = input('A summary file will be generated, enter the name of the output file: ')
print('')
print('Enter the Algolia credentials')
APP_ID = input('Enter the Algolia APP ID: ')
API_KEY = input('Enter the Algolia Admin API KEY: ')
INDEX_NAME = input('Enter the Algolia index name: ')
print('')
print('-- additional info --')
name_att = input('Enter the name of the attribute that contains the name of the object: (default is "name"): ')
if name_att not in ['', None]:
    NAME_ATT = name_att

BATCH_SIZE = 500

objectIDs = []
object_dict = {}

client = init_algolia_client(APP_ID, API_KEY, BATCH_SIZE)

index = client.init_index(INDEX_NAME)
count_duplicates = 0
# get all objectIDs from the CSV file, the object IDs are in column 0 of the CSV file
print('reading input file...')
with open(INPUT_FILE, 'r') as f:
    for line in f:
        #skip the first line
        objectID = str(line.split(',')[-1]).strip()
        if 'object_id' in objectID:
            continue

        if objectID not in objectIDs:
            objectIDs.append(objectID)
            object_dict[objectID] = {'objectID': objectID, NAME_ATT: line[:-len(objectID)+1]}
        else:
            #print(f"Object already exists in the list: ", line)
            record = object_dict[objectID]
            record[NAME_ATT] = record[NAME_ATT] + ' | ' + line[:-len(objectID)+1]
#            object_dict[objectID][NAME_ATT] = object_dict[objectID][NAME_ATT] + ' | ' + line[:-len(objectID)+1]
            count_duplicates += 1
if count_duplicates > 0:
    print(f"found {count_duplicates} duplicate objects in the input file")
    print(f"remaining objects: {len(objectIDs)}")

print('writing missing records to output file...')
#check if output file exists and ask user if he wants to overwrite it
try:
    with open(OUTPUT_FILE, 'r') as f:
        print('Output file already exists, do you want to overwrite it?')
        overwrite = input('yes/no: ')
        if overwrite == 'yes':
            with open(OUTPUT_FILE, 'w') as f:
                f.write('')
        else:
            print('Exiting')
            exit()
except:
    print('Error opening output file, does not exist? Creating new file')

# get the objects from Algolia index, retrieve batches of 1000 objects
total_count = 0
count = 0
print('checking index, getting objectIDs 1000 at a time...')
for i in range(0, len(objectIDs), 1000):
    print('getting objects from Algolia index, batch {} of {}'.format(i, len(objectIDs)))
    batch = objectIDs[i:i+1000]
    result = index.get_objects(batch, {
        'attributesToRetrieve': [NAME_ATT]
    })

    #print('message: ', result['message'])

    # Regular expression pattern to match numbers
    pattern = r'ObjectID\s+(\w+)'

    # Find all matches of the pattern in the string
    numbers = re.findall(pattern, result['message'])
    print(f"found {len(numbers)} objects in Algolia index")
    total_count += len(numbers)
    #write result to json file
    with open(OUTPUT_FILE, 'a') as f:
        json.dump(result, f, indent=4)

    missing_objects = []
    for number in numbers:
        if str(number) not in object_dict:
            print(f"Object with objectID {number} not found")
            continue
        missing_objects.append(object_dict[str(number)])
    
    #send missing objects to Algolia index
    count, failed_records = send_data_to_algolia(client, missing_objects, INDEX_NAME, count, [])

print(f"Total number of objects not found in Algolia index: {total_count}")
print(f"Total number of objects added to Algolia index: {count}")
print(f"Total number of objects failed to add to Algolia index: {len(failed_records)}")