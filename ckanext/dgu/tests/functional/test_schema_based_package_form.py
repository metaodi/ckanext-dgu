"""
High-level functional tests for the create/edit package form.

The new package form is being refactored so as not to use sqlalchemy.  These
are the tests for this form.  For tests based on the sqlalchemy-based form,
see 'test_package_gov3.py'.
"""
import re

from nose.plugins.skip import SkipTest

from ckanext.dgu.tests import Gov3Fixtures

from ckan.lib.field_types import DateType
from ckan.tests import WsgiAppCase, CommonFixtureMethods
from ckan.tests.html_check import HtmlCheckMethods

def url_for(**kwargs):
    """
    TODO: why isn't the real url_for picking up the correct route?
    """
    from ckan.tests import url_for as _url_for
    url = _url_for(**kwargs)
    return url.replace('dataset','package')

class TestFormRendering(WsgiAppCase, HtmlCheckMethods, CommonFixtureMethods):
    """
    Tests that the various fields are represeted correctly in the form.
    """

    # Fields we expect to see on the rendered form.
    # input name -> (Label text , input type)
    # for example:
    #   <label for="title">Title *</label>
    #   <input name="title"/>
    _expected_fields = {
        # Basic information
        'title':     ('Title *', 'input'),
        'name':      ('Identifier *', 'input'),
        'notes':     ('Abstract *', 'textarea'),
        
        # Details
        'date_released':                ('Date released', 'input'),
        'date_updated':                 ('Date updated', 'input'),
        'date_update_future':           ('Date to be published', 'input'),
        'update_frequency':             ('Update frequency', 'select'),
        'update_frequency-other':       ('Other:', 'input'),
        'precision':                    ('Precision', 'input'),
        'geographic_granularity':       ('Geographic granularity', 'select'),
        'geographic_granularity-other': ('Other', 'input'),
        'geographic_coverage':          ('Geographic coverage', 'input'),
        'temporal_granularity':         ('Temporal granularity', 'select'),
        'temporal_granularity-other':   ('Other', 'input'),
        'temporal_coverage':            ('Temporal coverage', 'input'),
        'url':                          ('URL', 'input'),
        'taxonomy_url':                 ('Taxonomy URL', 'input'),

        # Resources
        # ... test separately

        # More details
        'published_by':         ('Published by *', 'select'),
        'published_via':        ('Published via', 'select'),
        'author':               ('Contact', 'input'),
        'author_email':         ('Contact email', 'input'),
        'mandate':              ('Mandate', 'input'),
        'license_id':           ('Licence *', 'select'),
        'tag_string':           ('Tags', 'input'),
        'national_statistic':   ('National Statistic', 'input'),

        # After fieldsets
        'log_message':  ('Edit summary', 'textarea'),

    }
    
    # Fields that shouldn't appear in the form
    _unexpected_fields = (
        'external_reference',
        'import_source',
        'version',
        'maintainer',
        'maintainer_email',
        'newfield0-key',
        'newfield0-value',
    )

    @classmethod
    def setup(self):
        """
        Create standard gov3 test fixtures for this suite.

        This test class won't be editing any packages, so it's ok to only
        create these fixtures once.
        """
        self.fixtures = Gov3Fixtures()
        self.fixtures.create()

    @classmethod
    def teardown(self):
        """
        Cleanup the Gov3Fixtures
        """
        self.fixtures.delete()

    def test_new_form_has_all_fields(self):
        """
        Asserts that a form for a new package contains the various expected fields
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset)

        # quick check that we're checking the correct url
        assert "package" in offset

        for field, (label_text, input_type) in self._expected_fields.items():

            # e.g. <label for="title">Title *</label>
            self.check_named_element(response.body,
                                     'label',
                                     'for="%s"' % field,
                                     label_text)

            # e.g. <input name="title">
            self.check_named_element(response.body,
                                     input_type,
                                     'name="%s' % field)

    def test_new_form_does_not_contain_unexpected_fields(self):
        """
        Asserts that the fields named in self._unexpected_fields do not appear in the form.

        There are a set of fields that are on the normal package form that we don't
        want appearing in the dgu form.
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset)

        for field in self._unexpected_fields:
            match = re.search('<(input|textarea|select) [^>]* name="%s"' % field,
                              response.body)
            assert not match , '"%s" found in response: "%s"' % (field, match.group(0))

    def test_edit_form_form_has_all_fields(self):
        """
        Asserts that edit-form of a package has the fields prefilled correctly.
        """
        package = self.fixtures.pkgs[0]

        offset = url_for(controller='package', action='edit', id=package['name'])
        response = self.app.get(offset)

        # form field name -> expected form field value
        expected_field_values = {}

        # populate expected_field_values with the simple fields first
        for field_name in self._expected_fields:
            try:
                expected_value = package[field_name]
                if isinstance(expected_value, basestring):
                    expected_field_values[field_name] = expected_value
            except KeyError:
                pass

        # populate expected_field_values for tag_string and license_id
        # by hand, as the field names in the package dict don't follow the
        # same naming scheme as the form fields.
        expected_field_values['tag_string'] = package['tags']
        expected_field_values['license_id'] = package['license']

        # Promote the key-value pairs stored in 'extras' to form fields.
        expected_field_values.update((k,v) for (k,v) in package['extras'].items()\
                                           if k not in self._unexpected_fields)

        # Some of the data isn't in the format as rendered on the form, so
        # overwrite it by hand for now.
        expected_field_values['geographic_coverage'] = 'england'
        date_fields = ('date_update_future',
                       'date_released',
                       'date_updated',
                       'temporal_coverage-from',
                       'temporal_coverage-to',
                       )
        for field_name in date_fields:
            expected_field_values[field_name] = _convert_date(expected_field_values[field_name])

        # TODO: fix these fields
        del expected_field_values['published_by']
        del expected_field_values['published_via']
    
        for field_name, expected_value in expected_field_values.items():
            self.check_named_element(response.body,
                                     '(input|textarea)',
                                     'name="%s"' % field_name,
                                     expected_value)

    def test_edit_form_does_not_contain_unexpected_fields(self):
        """
        Asserts that the fields named in self._unexpected_fields do not appear in the form.

        There are a set of fields that are on the normal package form that we don't
        want appearing in the dgu form.
        """
        package = self.fixtures.pkgs[0]

        offset = url_for(controller='package', action='edit', id=package['name'])
        response = self.app.get(offset)

        for field in self._unexpected_fields:
            match = re.search('<(input|textarea|select) [^>]* name="%s"' % field,
                              response.body)
            assert not match , '"%s" found in response: "%s"' % (field, match.group(0))

class TestFormValidation(WsgiAppCase):
    """
    A suite of tests that check validation of the various form fields.
    """

    def test_title_non_empty(self):
        """Asserts that the title cannot be empty"""
        data = {'title': ''}
        response = self._post_form(data)
        assert 'Title: Missing value' in response.body

    def test_name_non_empty(self):
        """Asserts that the name (uri identifier) is non-empty"""
        data = {'name': ''}
        response = self._post_form(data)
        assert 'Name: Missing value' in response.body

    def test_name_rejects_non_alphanumeric_names(self):
        """Asserts that the name (uri identifier) does not allow punctuation"""
        bad_names = ('fullstop.',
                     'exclamation!',
                     'quotes"',
                     'hash#',
                     'unicode%E3%82%A1', # u'unicode\u30a1' url-encoded
                     )
        for name in bad_names:
            data = {'name': name}
            response = self._post_form(data)
            assert 'Url must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'\
                in response.body, '"%s" allowed as url identifier' % name

    def test_name_must_be_at_least_2_characters(self):
        """Asserts that 1-length names are not allowed"""
        data = {'name': 'a'}
        response = self._post_form(data)
        assert 'Name must be at least 2 characters long' in response.body

    def test_notes_non_empty(self):
        """Asserts that the abstract cannot be empty"""
        data = {'notes': ''}
        response = self._post_form(data)
        assert 'Notes: Missing value' in response.body

    def test_date_released_only_accepts_well_formed_dates(self):
        """
        Asserts that date_released only accepts dates.
        
        TODO: what's the granularity of this field meant to be?  Schema indicates
              it's very loose, e.g. "Dec/2011", whereas form help indicates it's
              to the day.
        TODO: are these even on the new form?
        """
        raise SkipTest('date_released field needs spec.')

    def test_date_updated_only_accepts_well_formed_dates(self):
        """
        Asserts that date_updated only accepts dates.
        
        TODO: what's the granularity of this field meant to be?  Schema indicates
              it's very loose, e.g. "Dec/2011", whereas form help indicates it's
              to the day.
        TODO: are these even on the new form?
        """
        raise SkipTest('date_updated field needs spec.')

    def test_date_update_future_only_accepts_well_formed_dates(self):
        """
        Asserts that date_update_future only accepts dates.
        
        TODO: what's the granularity of this field meant to be?  Schema indicates
              it's very loose, e.g. "Dec/2011", whereas form help indicates it's
              to the day.
        TODO: are these even on the new form?
        """
        raise SkipTest('date_update_future field needs spec.')

    def _post_form(self, data):
        """
        GETs the package-create page, fills in the given fields, and POSTs the form.
        """
        offset = url_for(controller='package', action='new')
        response = self.app.get(offset)
        
        # parse the form fields from the html
        form_field_matches = re.finditer('<(input|select|textarea) [^>]* name="(?P<field_name>[^"]+)"',
                                         response.body)

        # initialise all fields with an empty string
        form_fields = dict((match.group('field_name'), '') for match in form_field_matches)
        form_fields['save'] = 'Save'
        
        # and fill in the form with the data provided
        form_fields.update(data)
        return self.app.post(offset, params=form_fields)

def _convert_date(datestring):
    """
    Converts a date-string to that rendered by the form.

    It does this by converting to db format, and then back to a string.
    """
    return DateType.db_to_form(datestring)