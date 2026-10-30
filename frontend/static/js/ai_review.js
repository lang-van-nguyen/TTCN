function analyze() {
    const review = document.getElementById("review").value;
    const resultBox = document.getElementById("result");
    const sentimentText = document.getElementById("sentimentText");
    const confidenceText = document.getElementById("confidenceText");
    const progress = document.querySelector(".progress");
    const progressBar = document.getElementById("progressBar");

    if (!review.trim()) {
        alert("Vui lòng nhập bình luận!");
        return;
    }

    // ✅ GỌI ĐÚNG API LƯU DB
    fetch("http://127.0.0.1:5000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            text: review   // ⚠️ BẮT BUỘC là text
        })
    })
    .then(res => res.json())
    .then(data => {
        const sentiment = data.sentiment;
        const confidence = data.confidence;

        resultBox.classList.remove("hidden");

        if (sentiment === "positive") {
            sentimentText.textContent = "🟢 TÍCH CỰC";
            sentimentText.className = "positive";
            progress.className = "progress positive";
        } else if (sentiment === "negative") {
            sentimentText.textContent = "🔴 TIÊU CỰC";
            sentimentText.className = "negative";
            progress.className = "progress negative";
         }// else {
        //     sentimentText.textContent = "🟡 TRUNG LẬP";
        //     sentimentText.className = "neutral";
        //     progress.className = "progress neutral";
        // }

        progressBar.style.width = (confidence * 100) + "%";
        confidenceText.textContent =
            `Độ tin cậy: ${(confidence * 100).toFixed(2)}%`;
    })
    .catch(() => {
        alert("Không kết nối được server!");
    });
}
