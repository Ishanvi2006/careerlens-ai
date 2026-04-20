console.log("JS Loaded");

async function handleSubmit() {
    try {
        const fileInput = document.getElementById("resume");
        const jd = document.getElementById("jd").value;

        if (!fileInput.files[0]) {
            alert("Please upload a resume");
            return;
        }

        const formData = new FormData();
        formData.append("resume", fileInput.files[0]);
        formData.append("job_description", jd);

        const response = await fetch("http://127.0.0.1:5000/upload", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        document.getElementById("score").innerText = data.match_score;

        const matchedList = document.getElementById("matched");
        matchedList.innerHTML = "";
        data.matched_skills.forEach(skill => {
            const li = document.createElement("li");
            li.innerText = skill;
            matchedList.appendChild(li);
        });

        const missingList = document.getElementById("missing");
        missingList.innerHTML = "";
        data.missing_skills.forEach(skill => {
            const li = document.createElement("li");
            li.innerText = skill;
            missingList.appendChild(li);
        });

    } catch (error) {
        console.error(error);
        alert("Error occurred");
    }
}