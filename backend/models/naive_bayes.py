import math
from collections import defaultdict


class NaiveBayes:
    """
  
    """

    def __init__(self):
        self.class_count = defaultdict(int)
        self.word_count = defaultdict(lambda: defaultdict(int))
        self.total_words = defaultdict(int)

        self.vocab = set()
        self.total_docs = 0

    # TRAIN MODEL
    def train(self, data):
        """
        data: list các tuple (tokens, label)
        tokens: list từ đã preprocess
        label: 'positive' hoặc 'negative'
        """

        for tokens, label in data:
            self.class_count[label] += 1
            self.total_docs += 1

            for word in tokens:
                self.word_count[label][word] += 1
                self.total_words[label] += 1
                self.vocab.add(word)

    # PRIOR PROBABILITY
    def prior(self, label):
        """
        P(class)
        """
        return self.class_count[label] / self.total_docs

 
    def likelihood(self, word, label):
        """
        P(word | class) với Laplace smoothing
        """
        word_freq = self.word_count[label].get(word, 0)
        return (word_freq + 1) / (self.total_words[label] + len(self.vocab))

 
    def predict(self, tokens):
        """
        tokens: list từ đã preprocess
        return: label dự đoán
        """

        scores = {}

        for label in self.class_count:

            score = math.log(self.prior(label))

            for word in tokens:
                score += math.log(self.likelihood(word, label))

            scores[label] = score

        # Lấy lớp có xác suất cao nhất
        return max(scores, key=scores.get)

    def predict_with_prob(self, tokens):
        """
        Trả về:
        - label dự đoán
        - xác suất tương đối
        """

        log_scores = {}

        for label in self.class_count:
            score = math.log(self.prior(label))
            for word in tokens:
                score += math.log(self.likelihood(word, label))
            log_scores[label] = score

        # Softmax để chuyển log-score → probability
        max_log = max(log_scores.values())
        exp_scores = {
            label: math.exp(log_scores[label] - max_log)
            for label in log_scores
        }

        total = sum(exp_scores.values())
        probs = {label: exp_scores[label] / total for label in exp_scores}

        predicted_label = max(probs, key=probs.get)

        return predicted_label, probs
