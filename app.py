from GraphFormatter import GraphFormatter

if __name__ == "__main__":
    app = GraphFormatter("config_updated.yml")  # path to your YAML
    app.app.run(debug=True)
