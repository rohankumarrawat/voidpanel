function sendmessage(event) {
    event.preventDefault();
    var message = document.getElementById('message').value;
    var data = {
        'message': message,

    };
    // The HTML string to be added
    const newChatBox = `
<div class="chat-box author-speech bg-flashlight">
</div>
`;

    document.getElementById('message').value = "";
    const targetContainer = document.getElementById('adminchat');
    if (targetContainer) {
        targetContainer.insertAdjacentHTML('beforeend', newChatBox);

    } else {
        console.error('Target container with ID "adminchat" not found!');
    }
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: 'smooth'
    });
    let insideCodeBlock = false;
    fetch("{% url 'chatmessage' %}", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify(data)
    })
        .then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let done = false;
            document.getElementById('action').style.display = "block";

            const voidpanelai = `<div class="chat-box ai-speech bg-flashlight">
                   

                </div>`;

            targetContainer.insertAdjacentHTML('beforeend', voidpanelai);
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth' // Adds smooth scrolling
            });
            let insideCodeBlock = false;

            let insideCodeBlockk = false;
            let currentCode = "";
            function logStream() {
                reader.read().then(({ value, done: streamDone }) => {
                    if (streamDone) {
                        document.getElementById('action').style.display = "none";

                        console.log("Chat complete");
                       

                        // Hide the divs with the class 'letget' once streaming is complete
                        const divs = document.querySelectorAll('.letget');
                        divs.forEach(div => {
                            div.style.display = 'none';
                        });


                        return;
                    }

                    // Decode and log the streamed chunk
                    const chunk = decoder.decode(value, { stream: true });

                    const latestParagraph = document.querySelectorAll('.contentedit');

                    const lastParagraph = latestParagraph[latestParagraph.length - 1];

                    const latestParagraphcode = document.querySelectorAll('.codeadd');

                    const lastParagraphcode = latestParagraphcode[latestParagraphcode.length - 1];
                    if (chunk.startsWith("```") || chunk.startsWith("``")) {
                        // Handle start or end of the code block
                        if (insideCodeBlock) {
                            // Closing the code block
                            insideCodeBlock = false;
                            currentCode = ""; // Reset the code block variable
                        } else {
                            // Opening the code block
                            insideCodeBlock = true;

                            // Check if the language name is included in this chunk
                            const matches = chunk.match(/```(\w+)?/);
                            if (matches && matches[1]) {
                                // Language name is on the same line
                                currentLanguage = matches[1];
                                chunk = ""; // Remove the language declaration
                            } else {
                                // Language will be in the next chunk
                                currentLanguage = null;
                            }

                            // Create a new <pre><code> block
                            var preBlock = document.createElement('pre');
                            var codeBlock = document.createElement('code');
                            var buttonblock = document.createElement('button');

                            buttonblock.textContent = 'Copy Code';


                            codeBlock.className = `codeadd45 ${currentLanguage || ""}`;
                            buttonblock.className = `copy-btn`;
                            buttonblock.setAttribute('onclick', 'copyfunction(this)');
                            preBlock.className = `code-container`;

                            preBlock.appendChild(codeBlock);
                            preBlock.appendChild(buttonblock);
                            lastParagraph.appendChild(preBlock);
                        }
                    } else if (insideCodeBlock) {
                        // Add content inside the code block
                        const codeBlock = document.querySelectorAll('.codeadd45');
                        const codeBlockk = codeBlock[codeBlock.length - 1];


                        if (codeBlockk) {
                            if (!currentLanguage && chunk.trim()) {

                                currentLanguage = chunk.trim();
                                codeBlockk.className = `codeadd45 ${currentLanguage}`;

                            } else {




                                // Append the chunk as code
                                try {

                                    codeBlockk.innerHTML += chunk; // Append new content


                                } catch (error) {
                                    console.error("Error updating code block:", error);
                                }
                            }
                        } else {
                            console.error("No code block found to append content");
                        }
                    } else {
   
                        lastParagraph.innerHTML += chunk;
                    }
                    window.scrollTo({
                        top: document.body.scrollHeight,
                        behavior: 'smooth' // Adds smooth scrolling
                    });

                    // Continue reading the stream
                    logStream();
                });
            }

            logStream();
        })
        .catch(error => console.error("Streaming error:", error));

}