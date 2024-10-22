#include "test.hpp"
#include <lexbor/html/parser.h>
#include <lexbor/html/interfaces/document.h>

const char* test() {
    static const lxb_char_t html[] = "<div>Works fine!</div>";
    size_t html_len = sizeof(html) - 1;

    lxb_html_document_t *document = lxb_html_document_create();
    if (document == NULL) {
        exit(EXIT_FAILURE);
    }

    lxb_status_t status = lxb_html_document_parse(document, html, html_len);
    if (status != LXB_STATUS_OK) {
        exit(EXIT_FAILURE);
    }

    const lxb_char_t *tag_name = lxb_dom_element_qualified_name(lxb_dom_interface_element(document->body),
                                                                NULL);

    printf("Element tag name: %p\n", tag_name);

    lxb_html_document_destroy(document);
    return "Hello, World!";
}