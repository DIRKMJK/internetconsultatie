Download metadata of, and individual responses to, Dutch government online consultations. Note that the code is provided as is and may contain errors; please check the results.

# Background 

During the preparation of new legislation and regulations, the Dutch government often holds an online consultation to gather feedback. People who respond to a consultation can decide whether their response may be published. Public responses are available online. The `internetconsultatie` package collects and analyses public responses.

# Download metadata

To download metadata of all closed consultations:

```python
from internetconsultatie import download_consultations

download_consultations()
```

Metadata includes the name of the organisation that held the consultation, topics, start date, end date, and number of responses.

The results will be saved as an excel file. You can set the location where the results are stored using the optional `dir_responses` parameter (the default location is `../data/`).

If you want to store the html code of each consultation web page for further analysis, you can set `html=True` (and, optionally, `dir_html`). This web page will contain a summary of the proposed legislation or regulation.

If downloading is for some reason interrupted, you can rerun the code; it will skip results already downloaded.

# Download responses

To download responses to a specific consultation, get the name of the consultation from its url, for example:

```python
from internetconsultatie import download_responses

name = 'wijzigingbesluitenregelingwetinvoeringminimumuurloon'
download_responses(name)
```

The results will be saved as an excel file. If downloading is for some reason interrupted, you can rerun the code; it will skip results already downloaded.

You can use the following parameters:

- `consultation`: name of the consultation, taken from its url
- `name`: if True, the name of respondent will be saved (default False)
- `dir_responses`: directory where responses will be saved (default '../data')
- `download_attachments`: if True, attachments will be downloaded (default True)
- `dir_attachments`: directory where attachments will be saved (default '../data/attachments')
- `extract_text_attachment`: if True, text will be extracted from attachments and stored in a column 'text_attachment', using `textract` (default True)
- `components`: if True, groups of similar responses will be identified in a column 'component'. Responses are compared pragmatically by extracting ngrams and then calculating jaccard similarity (default True)
- `n`: n to be used to extract ngrams if `component` is set (default 5)
- `threshold`: threshold value to determine if texts are similar, based on jaccard similarity of ngrams, if `component` is set  (default 0.3)

Organisations sometimes mobilise their members to submit responses, often providing them with an example text they can use. The component value can be used as a pragmatic tool to analyse such campaigns.

Note that if you download responses without extracting the attachment text and identifying components, you can do so later (you’ll need to specify the path to the excel file with downloaded responses):

```python
import pandas as pd
from internetconsultatie import add_components

df = pd.read_excel(path_responses)
df = add_components(df)

```