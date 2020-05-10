import argparse
import csv

from tqdm import tqdm
import jsonlines
import spacy

# Command line arguments.
parser = argparse.ArgumentParser(description='Create relationship .csv file using'
                                             ' SciSpacy\'s en_ner_jnlpba_md NER model.')

parser.add_argument('--in_file', type=str,
                    default='data/CORD-NER-PROTEIN-corpus.jsonl',
                    help='Filepath to jsonl file which contain the sentences to create relations from.')
parser.add_argument('--out_file', type=str, default='data/relations.csv',
                    help='csv output file to which CORD-NER protein entity-containing relations'
                         'will be written (header: doc_id, sent, triple, analysis)')
args = parser.parse_args()
fi = args.in_file
fo = args.out_file

nlp = spacy.load('en_ner_jnlpba_md')

def open_ner_data(fi):
    with jsonlines.open(fi) as reader:
        data = [line for line in tqdm(reader, desc="Opening file")]
    return data

def create_string(tokenized_sent):
    return  ' '.join(tokenized_sent)

def create_text_doc(data):
    text = [(create_string(sent['sent_tokens']), doc['doc_id'], sent['sent_id']) for doc in data for sent in doc['sents']]
    # return ' '.join(text)
    return text

def extract_text(data):
    return [(doc['doc_id'], doc['sent'], doc['doi']) for doc in data]

def parse(data):
    triples = []
    text = extract_text(data)
    for (doc_id, sent, doi) in tqdm(text, desc="Parsing sentences"):
        doc = nlp(sent)
        triple = {}
        for token in doc:
            if token.dep_ == "ROOT":
                triple.update({'doc_id': doc_id, 'sent': sent, 'doi': doi})
                triple_lst = [token.lemma_]
                relation_lst = [token]
                for child in token.children:
                    if child.pos_  not in ["PUNCT", "AUX"] and \
                        child.text not in ['it', 'there'] and \
                        child.dep_ != 'advmod': #exclude auxes, punc, expletives and adverbal modifiers

                        left_edge = child.left_edge.i
                        right_edge = child.right_edge.i + 1
                        triple_lst.append(doc[left_edge:right_edge].text)
                        relation_lst.append(doc[left_edge:right_edge])

                if len(triple_lst) > 1:
                    triple.update({'triple': triple_lst})
                    token = relation_lst[0]
                    dep_relations = [[token.text, token.dep_, token.head.text]]
                    for span in relation_lst[1:]:
                        span_lst =[]
                        for token in span:
                            span_lst.append((token.text, token.dep_, token.head.text))
                        dep_relations.append(span_lst)
                    triple.update({'analysis': dep_relations})
                    triples.append(triple)
    return triples

if __name__ == '__main__':
    data = open_ner_data(fi)
    triples = parse(data)
    with open(fo, 'w', encoding='utf-8') as output_file:
        fieldnames = list(triples[0].keys())
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for relation in tqdm(triples, desc="Writing file"):
            writer.writerow(relation)