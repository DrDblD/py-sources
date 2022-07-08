import pandas

df = pandas.read_csv("/home/atab/repos/py-sources/All-Messages-search-result.csv")
ndf = df.message.value_counts()
open("/home/atab/repos/py-sources/All-Messages-search-result.html", "w").write(ndf.to_html()).close()