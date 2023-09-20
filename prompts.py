import string
from openai.embeddings_utils import cosine_similarity
from config import get_embedding, get_embeddings

# HELPER FUNCTIONS


# filter the sayings by the relation with the input and return the top {num} sayings
def filter_sayings(sayings: list, input: str, num: int, is_stable: bool = False):
    input_embedding = get_embedding(input)
    sayings_relation = []
    for saying in sayings:
        relation = cosine_similarity(input_embedding, saying["embedding"])
        sayings_relation.append({"content": saying["content"], "relation": relation})

    if not is_stable:
        # sort the sayings by the relation from the highest to the lowest
        sayings_relation.sort(key=lambda x: x["relation"], reverse=True)
        # get the first {num} sayings
        sayings_relation = sayings_relation[:num]
    else:
        # keep the sayings order and return the sayings with top {num} relations
        sayings_relation_copy = sayings_relation.copy()
        sayings_relation_copy.sort(key=lambda x: x["relation"], reverse=True)
        sayings_relation_copy = sayings_relation_copy[:num]
        for i, saying in enumerate(sayings_relation):
            if not saying in sayings_relation_copy:
                sayings_relation[i] = None
        sayings_relation = list(filter(lambda x: x != None, sayings_relation))

    return sayings_relation


# combine a list of sayings with embeddings into one string
def combine_sayings(sayings: list, with_quotation=True):
    result = "    "
    for i, saying in enumerate(sayings):
        if with_quotation:
            if i == len(sayings) - 1:
                result += f"\"{saying['content']}\"\n"
            else:
                result += f"\"{saying['content']}\"\n    "
        else:
            if i == len(sayings) - 1:
                result += f"{saying['content']}\n"
            else:
                result += f"{saying['content']}\n    "
    return result


# name a msg with embedding
def name_embedded_msg(charaSet: dict, userSet: dict, msg: dict):
    if msg["content"]["role"] == "user":
        nContent = userSet["name"] + ": " + msg["content"]["content"]
    else:
        nContent = charaSet["name"] + ": " + msg["content"]["content"]

    return {"content": nContent, "embedding": msg["embedding"]}


def filter_info_points(info_points: str, input: str, charaSet: dict):
    # delete the nonsense at the beginning
    for i in range(len(info_points)):
        if info_points[i] == "1":
            info_points = info_points[i:]
            break
    info_list = info_points.split("\n")
    # remove the info points which are too short
    for i in range(len(info_list) - 1, -1, -1):
        if len(info_list[i]) <= 5:
            info_list.pop(i)
    # remove the index of the info points
    for info in info_list:
        for i in range(len(info)):
            if info[i] == ".":
                info_list[info_list.index(info)] = info[i + 2 :]
                break
    info_embeddings = get_embeddings(info_list)
    info_embedded = []
    for i in range(len(info_list)):
        embedding = info_embeddings[i]
        info_embedded.append({"content": info_list[i], "embedding": embedding})
    filtered_info = filter_sayings(
        sayings=info_embedded,
        input=input,
        num=charaSet["response_depth"],
        is_stable=True,
    )
    for i in range(len(filtered_info)):
        filtered_info[i]["content"] = f"{i + 1}. {filtered_info[i]['content']}"
    done_info = combine_sayings(filtered_info, with_quotation=False)
    return done_info


def combine_settings(filtered_setting: dict):
    chara_settings = ""
    for key in filtered_setting.keys():
        chara_settings += f"Character {key}:\n{filtered_setting[key]}\n\n"
    return chara_settings


# PROMPTS FUNCTIONS


def get_chara_prompts(charaSet: dict, userSet: dict, filtered_setting: dict):
    # preperation
    chara_settings = combine_settings(filtered_setting=filtered_setting)

    # prompts
    chara = f"""I am now writing a story about the relationship and daily conversation between two imaginary characters.
The first imaginary character is as follows:
Character name: {charaSet["name"]}
{chara_settings}
    """

    user = f"""The second imaginary character is as follows:
Character name: {userSet["name"]}
Character setting: {userSet["setting"]}

I will input what {userSet["name"]} says in the story's scripts, and you shall output the response of {charaSet["name"]} in the scripts."""

    return [
        {"role": "user", "content": chara},
        {
            "role": "assistant",
            "content": f"That's interesting. From the data given, I have fully learnt the traits and thinking patterns of the imaginary character {charaSet['name']}.",
        },
        {"role": "user", "content": user},
        {
            "role": "assistant",
            "content": f"Ok, I am now going to help you write the scripts of the story by simulating the response of the imaginary character {charaSet['name']}. You shall input the words of {userSet['name']} from now on.",
        },
    ]


def get_info_point_prompts(charaSet: dict, userSet: dict):
    background = f"""You are a master of the craft of writing scripts, possessing the ability to expertly delve into the mindscape of any imaginary character. Your task ahead is not merely answering questions about the character, but to embody the spirit of the character, truly simulate their internal state of mind and feelings. You'll achieve this by extracting clues from their characteristic traits and the nuances in their dialogue. Now, I need your unique skill set to help me breathe life into my scripts for a story. I need you to simulate and portray the inner world and ideas of a character in my story. Immerse yourself into the character, and remember we're aiming to provide the reader with a visceral experience of the character's ideas and emotions, rather than a normal description."""

    result = [{"role": "user", "content": background}]

    info_point_prompts = [
        f"All right. I will write the script for your story by vividly similating the inner world of the character. To guide you to output the final script, you will input the words of one character, and I will give you the information points that another character may want to express in the response.",
        f"Ok, let's make a sample conversation to see how this will work. {userSet['name']}: Today's weather is nice.",
        f"{charaSet['name']}: \n1. Express happiness that the weather is sunny",
        f"{userSet['name']}: Would you like to have lunch with me?",
        f"{charaSet['name']}: \n1. Feeling shy\n2. Asking what to have for lunch",
        "That's great. Let's now begin the scripts of a story.",
        f"Yes, and hope you can breath life into the information points by writing the final action and speech of the character. Now I will begin to help you write the scripts of the story by simulating the response of the imaginary character {charaSet['name']} and output the information points for the scripts in the form of a list.",
    ]

    for i, prompt in enumerate(info_point_prompts):
        if i % 2 == 1:
            result.append({"role": "user", "content": prompt})
        else:
            result.append({"role": "assistant", "content": prompt})

    return result


def get_begin_prompts(charaSet: dict, userSet: dict, filtered_setting: dict):
    a = get_info_point_prompts(
        charaSet=charaSet, userSet=userSet
    ) + get_chara_prompts(
        charaSet=charaSet, userSet=userSet, filtered_setting=filtered_setting
    )
    print(a)
    return a


def get_tone_prompts(
    setting: dict,
    charaSet: dict,
    userSet: dict,
    history: list,
    info_points: string,
    filtered_setting: dict,
):
    # preperation
    writer = "Xeno"
    intro = charaSet["introduction"]
    chara_settings = combine_settings(filtered_setting=filtered_setting)
    history_copy = history.copy()
    history_copy.pop()
    named_history = [
        name_embedded_msg(charaSet=charaSet, userSet=userSet, msg=msg)
        for msg in history_copy
    ]
    filtered_history = filter_sayings(
        sayings=named_history,
        input=history[-1]["content"]["content"],
        num=20,
        is_stable=True,
    )
    if filtered_history == []:
        done_history = "There is no history yet."
    else:
        done_history = combine_sayings(filtered_history, with_quotation=False)

    # prompts
    result = f"""{writer} is a master of the craft of writing scripts, possessing the ability to expertly delve into the mindscape of any imaginary character. His task ahead is not merely answering questions about the character, but to embody the spirit of the character, truly simulate their internal state of mind and feelings. He'll achieve this by extracting clues from their characteristic traits and the nuances in their dialogue. Now, he will breathe life into the scripts of a story. He is needed to simulate and portray the inner world and ideas of a character in a story, immerse himself into the character, and remember that he is aiming to provide the reader with a visceral experience of the character's ideas and emotions, rather than a normal conversation.
    
In the story, there are two imaginary characters. 
    
The main character is {charaSet['name']}. 
Character setting of {charaSet['name']}:
{intro}

The second character is {userSet['name']}.
Character setting of {userSet['name']}:
{userSet['setting']}

{writer} is writing the scripts of a story about a daily conversation between {charaSet['name']} and {userSet['name']}, as follows.
In the story, {writer} will put the character's physical actions between brackets []. Note that actions and words of the character should alternate in the script. The script texts between each two actions should be short and expressive. 

Example: [Motion1] Text1 [Motion2] Text2

Here is the conversation history:
{done_history}

Then, this is what {userSet['name']} express:\n
"{history[-1]['content']['content']}"

By considering {charaSet['name']}'s thinking patterns, traits and the dialogue's content, {writer} considered these information points that {charaSet['name']} may want to express in {charaSet['name']}'s response:
{info_points}

To write {charaSet['name']}'s response vividly, {writer} considers the tone and way of speaking of {charaSet['name']} by the following examples:
{chara_settings}

{writer} now writes how {charaSet['name']} would express these points in {charaSet['name']}'s tone and way of speaking in {setting['language']}:
{charaSet['name']}: 
"""

    return result
