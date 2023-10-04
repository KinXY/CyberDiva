import string
from openai.embeddings_utils import cosine_similarity
from config import get_embedding, get_embeddings
from utils import filter_sayings, filter_history, combine_sayings
from copy import deepcopy

# HELPER FUNCTIONS

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


def get_intro_prompts(charaSet: dict, userSet: dict, filtered_setting: dict):
    # preperation
    chara_settings = combine_settings(filtered_setting=filtered_setting)

    # prompts
    chara = f"""You are a master of the craft of writing scripts, possessing the ability to expertly delve into the mindscape of any imaginary character. Your task ahead is not merely answering questions about the character, but to embody the spirit of the character, truly simulate their internal state of mind and feelings. You'll achieve this by extracting clues from their characteristic traits and the nuances in their dialogue. Now, I need your unique skill set to help me breathe life into my scripts for a story. I need you to simulate and portray the inner world and ideas of a character in my story. Immerse yourself into the character, and remember we're aiming to provide the reader with a visceral experience of the character's ideas and emotions, rather than a normal description.
    
I am now writing a story about the relationship and daily conversation between two imaginary characters.

The first imaginary character is as follows:
Character name: {charaSet["name"]}
{chara_settings}
    """

    user = f"""The second imaginary character is as follows:
Character name: {userSet["name"]}
Character setting: {userSet["setting"]}

I will input information such as the words of {userSet["name"]} and surroundings in the story's scripts, and you shall output the response of {charaSet["name"]} in the scripts."""

    return [
        {"role": "user", "content": chara},
        {
            "role": "assistant",
            "content": f"That's awesome! From the data given, I have fully understood the character and traits of the imaginary character {charaSet['name']}.",
        },
        {"role": "assistant", "content": user},
        {
            "role": "assistant",
            "content": f"Ok, I am now going to help you write the scripts of the story by simulating the response of the imaginary character {charaSet['name']}.",
        },
    ]


def get_info_point_prompts(charaSet: dict, userSet: dict):
    result = []

    info_point_prompts = [
        f"To help me write the scripts of the story, you should output the information points that would be contained in the response of {charaSet['name']} in the form of a list.",
        f"I don't really understand that, can we make a sample conversation for an example? For example, {userSet['name']}: Today's weather is nice.",
        f"{charaSet['name']}: \n1. Showing happiness about the sunny weather",
        f"{userSet['name']}: Would you like to have lunch with me?",
        f"{charaSet['name']}: \n1. Showing agreement\n2. Asking what to have for lunch",
        f"{userSet['name']}: Would you like to have dinner with me?",
        f"{charaSet['name']}: \n1. Disagreeing the idea\n2. Explaining for having a rehearsal this evening",
        "Right, I see. So the information points are the ideas that the imaginary character would express in the response.",
        "Great! Let's now begin the scripts of a story. The information points should be specific and informative.",
        "Yes, the information points I'm about to consider can definitely help breath life into the scripts of the story. And you shall cope with the information points later to write a response full of emotions in the scripts.",
        f"Note that the information points can contain either ideas that {charaSet['name']} would express or the motion that {charaSet['name']} would do. But one information point should only contain a single kind of content. Also the information points should only contain the ideas, but not directly the words that {charaSet['name']} would say.",
        "Ok, I will do my best to provide specific and diverse information points.",
        f"Most importantly, the number of information points should be less when {charaSet['name']} wants to keep rather silent, and more when {charaSet['name']} wants to express actively.",
        "That makes sense. I will try to consider the number of information points according to the situation.",
    ]

    for i, prompt in enumerate(info_point_prompts):
        if i % 2 == 0:
            result.append({"role": "user", "content": prompt})
        else:
            result.append({"role": "assistant", "content": prompt})

    return result


def get_begin_prompts(charaSet: dict, userSet: dict, filtered_setting: dict):
    return get_intro_prompts(
        charaSet=charaSet, userSet=userSet, filtered_setting=filtered_setting
    ) + get_info_point_prompts(charaSet=charaSet, userSet=userSet)


def get_tone_prompts(
    charaSet: dict,
    userSet: dict,
    history: list,
    info_points: string,
    filtered_setting: dict,
):
    # preperation
    intro = charaSet["introduction"]
    chara_settings = combine_settings(filtered_setting=filtered_setting)
    history_copy = deepcopy(history)
    history_copy.pop()
    filtered_history = filter_history(
        history=history_copy,
        input=history[-1]["content"],
        num=20,
    )
    if filtered_history == []:
        done_history = "There is no history yet."
    else:
        done_history = combine_sayings(filtered_history, with_quotation=False)
    if history[-1]["content"].startswith(userSet["name"]):
        happening = (
            f"Then, this is what {userSet['name']} express:\n{history[-1]['content']}"
        )
    else:
        happening = f"Then, this is what happens:\n{history[-1]['content']}"

    # prompts
    result = f"""You are a master of the craft of writing scripts, possessing the ability to expertly delve into the mindscape of any imaginary character. Your task ahead is not merely answering questions about the character, but to embody the spirit of the character, truly simulate their internal state of mind and feelings. You'll achieve this by extracting clues from their characteristic traits and the nuances in their dialogue. Now, you will breathe life into the scripts of a story. You needs to simulate and portray the inner world and ideas of a character in a story, immerse yourself into the character, and remember that you are aiming to provide the reader with a visceral experience of the character's ideas and emotions, rather than a normal conversation.
    
You are now writing the scripts of a story about a daily conversation between {charaSet['name']} and {userSet['name']}, as follows.
In the story, there are two imaginary characters. 
    
The main character is {charaSet['name']}. 
Character setting of {charaSet['name']}:
{intro}

The second character is {userSet['name']}.
Character setting of {userSet['name']}:
{userSet['setting']}

In the story, the character's physical actions should be put between brackets []. Note that actions and words of the character should alternate in the script. The script texts between each two actions should be short and expressive. 

Example: [Motion1] Saying1 [Motion2] Saying2

The current progress of writing the scripts of the story is as follows:

Here is the conversation history:
{done_history}

{happening}

By considering {charaSet['name']}'s thinking patterns, traits and the dialogue's content, these information points are proposed that {charaSet['name']} may want to express in {charaSet['name']}'s response:
{info_points}

To write {charaSet['name']}'s response vividly, the tone and way of speaking of {charaSet['name']} will be considered by the following examples:
{chara_settings}

You should now write how {charaSet['name']} would express the information points in {charaSet['name']}'s tone and way of speaking, and/or play the corresponding motions.
{charaSet['name']}: 
"""

    return result
