from collections import Counter
import functions
import os
from dotenv import load_dotenv


def main():
    load_dotenv(r"C:\Users\radum\PycharmProjects\Gui project\PROIECT SEARCH ENGINE\.env")
    api_key=os.getenv("SERPER_API_KEY")
    api_key=functions.validate_api_key(api_key)

    user_input = input("Search: ")
    user_input_pages = int(input("How many pages to search: "))
    urls=functions.search_urls(user_input,user_input_pages,api_key)

    total_counter= Counter()
    bigram_counter= Counter()
    used_urls=[]
    min_freq = 3
    for u in urls:
        text = functions.get_page_text(u)
        if text is None:
            continue
        tokens=functions.text_filter(text)

        if tokens is None:
            continue
        bigram = zip(tokens, tokens[1:])
        bigram_counter.update(bigram)
        total_counter.update(tokens)
        used_urls.append(u)

    filtered_items=[(w,c) for w,c in total_counter.items() if c >= min_freq]
    filtered_counter=Counter(dict(filtered_items))
    top_result=filtered_counter.most_common(30)
    top_bigrams=[(" ".join(bg),c)for bg,c in bigram_counter.most_common(20) if c >= 2]

    termen=input("Specific word: \n")
    t=termen.lower().strip().replace("ş","ș").replace("ţ","ț")
    parts=[p for p in t.split() if p]
    if len(parts) == 1:
        w = parts[0]
        print(f"{w} : {total_counter.get(w,0)}")
    elif len(parts) == 2:
        w1,w2 = parts
        print(f"{w1} {w2}: {bigram_counter.get((w1,w2),0)}")
    else:
        print("1 or 2 words only!")
    for w,c in top_result:
        print(f"{w}:{c}")
    for bg,c in top_bigrams:
        print(f"{bg} : {c}")
    print("\nSurse folosite:")
    for u in used_urls:
        print(u)

main()
