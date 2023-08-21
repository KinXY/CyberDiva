import string
import openai
from openai.embeddings_utils import get_embedding, cosine_similarity

# filter the sayings by the relation with the input and return the top {num} sayings
def filter_sayings(sayings: list, input: string, api_key: string, num: int):
    openai.api_key = api_key
    input_embedding = get_embedding(text=input, engine="text-embedding-ada-002")
    sayings_relation = []
    for saying in sayings:
        relation = cosine_similarity(input_embedding, saying["embedding"])
        sayings_relation.append({"content": saying["content"], "relation": relation})

    # sort the sayings by the relation from the highest to the lowest
    sayings_relation.sort(key=lambda x: x["relation"], reverse=True)
    # get the first {num} sayings
    sayings_relation = sayings_relation[:num]
    return sayings_relation


def get_intro_prompts(charaSet: dict, userSet: dict, input: string, api_key: string):
    filtered_saying = filter_sayings(sayings=charaSet["sayings"], input=input, api_key=api_key, num=10)
    filtered_story = filter_sayings(sayings=charaSet["story"], input=input, api_key=api_key, num=3)

    chara = f"""I am now writing a story about the relationship and daily conversation between two imaginary characters.

The first imaginary character is as follows:

Character name: {charaSet["name"]}

Character sayings: 
    """

    for saying in filtered_saying:
        chara += saying["content"] + '\n    '
    chara = chara[:-4]
    chara += "Character story:\n    "
    for story in filtered_story:
        chara += story["content"] + '\n    '

    user = f"""The second imaginary character is as follows:

Character name: {userSet["name"]}

Character setting: {userSet["setting"]}

I will input what {userSet["name"]} says in the story, and you shall output the response of Klee in the story."""

    return [ {"role": "user", "content": chara}
           , {"role": "assistant", "content": f"Ok, I have fully understood the character and traits of the imaginary character {charaSet['name']}."}
           , {"role": "assistant", "content": user}
           , {"role": "assistant", "content": f"Ok, I am now going to help you write the story by simulating the response of the imaginary character {charaSet['name']}."}
           ]


def get_info_point_prompts(charaSet: dict, userSet: dict):
    result = []

    info_point_prompts = [ f"To help me write the story,  you should output the information points in the response of {charaSet['name']} in the form of a list."
                        , "Ok, let's make a sample conversation."
                        , f"{userSet['name']}: Would you like to have lunch with me?"
                        , f"{charaSet['name']}: \n- I'd love to\n- Asking what to have for lunch"
                        , "Ok, let's now begin a story."
                        ]

    for i, prompt in enumerate(info_point_prompts):
        if i % 2 == 0:
            result.append({"role": "user", "content": prompt})
        else:
            result.append({"role": "assistant", "content": prompt})
    
    end = f"Ok, in the story I will simulate the response of the imaginary character {charaSet['name']} and output the information points in the form of a list."

    result.append({"role": "assistant", "content": end})

    return result


def get_begin_prompts(charaSet: dict, userSet: dict):
    return get_intro_prompts(charaSet = charaSet, userSet = userSet) + get_info_point_prompts(charaSet = charaSet, userSet = userSet)


def get_tone_prompts(charaSet: dict, history: list, info_points: string):
    begin = f"""Here is a conversation between an imagined character called '{charaSet['name']}' and a human.
    
This is the sayings of '{charaSet['name']}':
    """

    for saying in charaSet["sayings"]:
        begin += saying["content"] + '\n    '

    begin += "The following is in a daily conversation:\n"

    input_prompt = f"This is the conversation history:\n"
    if len(history) == 0:
        input_prompt += "No history yet.\n"
    else:
        for msg in history:
            if msg["role"] == "user":
                role = "Human"
            else:
                role = charaSet["name"]
            sentence = msg["content"]
            input_prompt += (role + ": " + sentence + '\n')

    info_prompt = f"These are the points {charaSet['name']} wants to response to the human:\n"
    info_prompt += info_points + '\n'
    
    end = f"Here is how {charaSet['name']} would express this in {charaSet['name']}'s tone."

    return begin + info_prompt + end
