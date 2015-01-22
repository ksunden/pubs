from ..uis import get_ui
from ..configs import config
from .. import bibstruct
from .. import content
from .. import repo
from .. import paper
from .. import templates
from .. import apis


def parser(subparsers):
    parser = subparsers.add_parser('add', help='add a paper to the repository')
    parser.add_argument('bibfile', nargs='?', default = None,
                        help='bibtex file')
    parser.add_argument('-D', '--doi', help='doi number to retrieve the bibtex entry, if it is not provided', default=None)
    parser.add_argument('-d', '--docfile', help='pdf or ps file', default=None)
    parser.add_argument('-t', '--tags', help='tags associated to the paper, separated by commas',
                        default=None)
    parser.add_argument('-k', '--citekey', help='citekey associated with the paper;\nif not provided, one will be generated automatically.',
                        default=None)
    parser.add_argument('-c', '--copy', action='store_true', default=True,
            help="copy document files into library directory (default)")
    parser.add_argument('-C', '--nocopy', action='store_false', dest='copy',
            help="don't copy document files (opposite of -c)")
    return parser


def bibdata_from_editor(ui, rp):
    again = True
    bibstr = templates.add_bib
    while again:
        try:
            bibstr = content.editor_input(config().edit_cmd,
                                          bibstr,
                                          suffix='.bib')
            if bibstr == templates.add_bib:
                again = ui.input_yn(
                    question='Bibfile not edited. Edit again ?',
                    default='y')
                if not again:
                    ui.exit(0)
            else:
                bibdata = rp.databroker.verify(bibstr)
                bibstruct.verify_bibdata(bibdata)
                # REFACTOR Generate citykey
                again = False
        except ValueError:
            again = ui.input_yn(
                question='Invalid bibfile. Edit again ?',
                default='y')
            if not again:
                ui.exit(0)

    return bibdata

def command(args):
    """
    :param bibfile: bibtex file (in .bib, .bibml or .yaml format.
    :param docfile: path (no url yet) to a pdf or ps file
    """

    ui = get_ui()
    bibfile = args.bibfile
    docfile = args.docfile
    tags = args.tags
    citekey = args.copy

    rp = repo.Repository(config())

    # get bibtex entry
    if bibfile is None:
        if args.doi is None:
            bibdata = bibdata_from_editor(ui, rp)
        else:
            bibdata_raw = apis.doi2bibtex(args.doi)
            bibdata = rp.databroker.verify(bibdata_raw)
            if bibdata is None:
                ui.error('invalid doi {} or unable to retreive bibfile.'.format(args.doi))
                ui.exit(1)
                # TODO distinguish between cases, offer to open the error page in a webbrowser.
                # TODO offer to confirm/change citekey
    else:
        bibdata_raw = content.get_content(bibfile, ui=ui)
        bibdata = rp.databroker.verify(bibdata_raw)
        if bibdata is None:
            ui.error('invalid bibfile {}.'.format(bibfile))

    # citekey

    citekey = args.citekey
    if citekey is None:
        base_key = bibstruct.extract_citekey(bibdata)
        citekey = rp.unique_citekey(base_key)
    elif citekey in rp:
        ui.error('citekey already exist {}.'.format(citekey))
        ui.exit(1)

    p = paper.Paper(bibdata, citekey=citekey)

    # tags

    if tags is not None:
        p.tags = set(tags.split(','))

    # document file

    bib_docfile = bibstruct.extract_docfile(bibdata)
    if docfile is None:
        docfile = bib_docfile
    elif bib_docfile is not None:
        ui.warning(('Skipping document file from bib file '
                    '{}, using {} instead.').format(bib_docfile, docfile))

    # create the paper

    try:
        rp.push_paper(p)
        if docfile is not None:
            rp.push_doc(p.citekey, docfile, copy=args.copy)
            if args.copy:
                if ui.input_yn('The file {} has been copied to the pubs repository. Should the original be removed?'.format(docfile)):
                    content.remove_file(docfile)
    except ValueError as v:
        ui.error(v.message)
        ui.exit(1)
