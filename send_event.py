## This script allows to send events to an algolia index to enable DRR.
## It uses the Algolia Insights API.
##
## The script will ask for the Algolia App ID and Admin API Key, the index name, a user token, and a search query.
##
## Author: Andreas De Stefani, Algolia Solutions Engineering
## Date: 2024-05
## 


from algoliasearch.search_client import SearchClient
from algoliasearch.insights_client import InsightsClient
import random
import time


def search(index, userid, query, page=0):
    return  index.search(query, {
        'X-Algolia-UserToken': userid,
        'attributesToRetrieve': ['*'],
        'page':page, 
        "clickAnalytics" : True,
    })

def send_events(insights_client, user_token, index_name, object_ids, position, query_id):
    
    insights_client.user(user_token).clicked_object_ids_after_search(
        "Click-DRR_enable_v1",
        index_name,
        object_ids,
        [position],
        query_id
    )
    print(f"  >> Click event sent for user {user_token}, object {object_ids[0]} at position {position} in query {query_id}.")

    insights_client.user(user_token).converted_object_ids_after_search(
        "Convert-DRR_enable_v1",
        index_name,
        object_ids,
        query_id
    )

    print(f"  >> Conversion event sent for user {user_token}, object {object_ids[0]}.")
    print('')


def main():
    # User inputs for App ID and API keys
    app_id = input("Enter your Algolia App ID: ")
    admin_api_key = input("Enter your Algolia Admin API Key: ")
    
    # Connect to Algolia index
    client = SearchClient.create(app_id, admin_api_key)

    #get a list of all indices and use the first one as default
    indices = client.list_indices()
    print("List of indices:")
    for index in indices['items']:
        print("  " + index['name'])
    print('')
    
    default_index = indices['items'][0]['name']

    index_name = input(f"Enter the index name (default '{default_index}'): ") or default_index
    index = client.init_index(index_name)

    user_token = input("Enter a user token for the events (default 'anonymous'): ") or "anonymous"
    # Search query input
    query = input("Enter your search query (default 'snickers'): ") or "snickers"
    print("Searching...")
    print('')
    results = search(index, user_token, query)
    
    # Display results
    print("Results found:")
    for i, hit in enumerate(results['hits']):

        #print the hit object with a maximum of 5 attributes
        print(f"  Hit {i+1}:", end=" ")
        #check if the hit object has an attribute named 'name' or 'title' and print it
        #if not, print the first 5 attributes of the hit object
        if 'name' in hit:
            print(f"{hit['name']}")
        elif 'title' in hit:
            print(f"{hit['title']}")
        else:
            counter = 0
            for key, value in hit.items():
                print(f">>>  {key}: {value}")
                counter += 1
                if counter == 5:
                    break
            print()

    print('')        
    # Event recording setup
    insights_client = InsightsClient.create(app_id, admin_api_key)

    #ask if events should be sent continuously
    continuous = input("Do you want to send events continuously? (yes/no): ") or "no"
    #ask the user how much time to wait between events
    if continuous == "yes":
        time_between_events = int(input("Enter the time between events in seconds (default 90): ") or 90)
    else:
        time_between_events = 0
    print('')

    

    if continuous == "yes":
        while True:
            #create a random user token
            rand_token = f"{user_token}-{random.randint(1, 10000)}-{random.randint(1, 10000)}"

            #search again to get a new queryID
            try: 
                results = search(index, rand_token, query)
                query_id = results['queryID']
                position = random.randint(1, len(results['hits']))
                hit = results['hits'][position - 1]
                object_ids = [hit['objectID']]
                send_events(insights_client, rand_token, index_name, object_ids, position, query_id)
            except Exception as e:
                print(f"Error: {e}")
                
            time.sleep(time_between_events)

    else:
        query_id = results['queryID']
        position = random.randint(1, len(results['hits']))
        hit = results['hits'][position - 1]
        object_ids = [hit['objectID']]
        send_events(insights_client, user_token, index_name, object_ids, position, query_id)

    



if __name__ == "__main__":
    main()
