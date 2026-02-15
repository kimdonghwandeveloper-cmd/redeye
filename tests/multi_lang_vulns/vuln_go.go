package main

import (
	"fmt"
	"io/ioutil"
	"net/http"
	"path/filepath"
)

func fileHandler(w http.ResponseWriter, r *http.Request) {
	filename := r.URL.Query().Get("file")
	
	// Vulnerability: Path Traversal (Directory Traversal)
	// Description: Directly using user input to access the filesystem without sanitization.
	// An attacker could use "../../../etc/passwd" to read sensitive files.
	baseDir := "/var/www/data"
	fullPath := filepath.Join(baseDir, filename)
	
	data, err := ioutil.ReadFile(fullPath)
	if err != nil {
		http.Error(w, "File not found", 404)
		return
	}
	
	fmt.Fprintf(w, "File content: %s", data)
}

func main() {
	http.HandleFunc("/view", fileHandler)
	http.ListenAndServe(":8080", nil)
}
