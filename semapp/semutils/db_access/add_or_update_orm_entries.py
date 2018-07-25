# this is used for ORM updates from a dataframe
def add_or_update_orm_entries(df, session, TableClass, existing_check_col_table, existing_check_col_new):
    for count,data in df.iterrows():
        existing = session.query(TableClass).filter(getattr(TableClass,existing_check_col_table)==data[existing_check_col_new]).first()
        if existing:
            for c in df.columns:
                setattr(existing,c,data[c])
        else:
            kwargs = {}
            for c in df.columns:
                kwargs[c] = data[c]
            session.add(TableClass(**kwargs))


