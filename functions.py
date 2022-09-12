def send_email(email_address, info):
    pass


def fetch_all_with_columns(cursor_description, data):
  columns = [column[0] for column in cursor_description]
  result = []
  for value in data:
    tmp = {}
    for (index, column) in enumerate(value):
      tmp[columns[index]] = column
    result.append(tmp)

  return result


def fetch_one_with_columns(cursor_description, data):
  columns = [column[0] for column in cursor_description]
  result = {}
  for (index, column) in enumerate(data):
    result[columns[index]] = column

  return result