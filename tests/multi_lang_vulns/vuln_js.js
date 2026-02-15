const express = require('express');
const app = express();

app.get('/search', (req, res) => {
    const query = req.query.q;

    // Vulnerability: Reflected XSS
    // Description: Directly outputting user-provided query to the response without escaping.
    res.send(`<h1>Search results for: ${query}</h1>`);
});

app.get('/calc', (req, res) => {
    const expression = req.query.expr;

    // Vulnerability: Code Injection
    // Description: Using eval() on user-provided input.
    try {
        const result = eval(expression);
        res.send(`Result: ${result}`);
    } catch (e) {
        res.status(500).send("Error");
    }
});

app.listen(3000, () => console.log('Server running on port 3000'));
