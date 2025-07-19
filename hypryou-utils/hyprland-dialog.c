#include <gtk/gtk.h>
#include <stdlib.h>

typedef struct
{
    gchar *title;
    gchar *apptitle;
    gchar *text;
    gchar *buttons_raw;
} DialogOptions;

static gchar *strip_markup_and_convert_br(const gchar *input)
{
    GString *out = g_string_new("");
    const gchar *p = input;

    while (*p)
    {
        if (g_ascii_strncasecmp(p, "<br", 3) == 0)
        {
            const char *gt = strchr(p, '>');
            if (gt)
            {
                g_string_append_c(out, '\n');
                p = gt + 1;
                continue;
            }
        }

        if (*p == '<')
        {
            const char *gt = strchr(p, '>');
            if (gt)
            {
                p = gt + 1;
            }
            else
            {
                p++;
            }
        }
        else
        {
            g_string_append_c(out, *p++);
        }
    }

    return g_string_free(out, FALSE);
}

static void
on_button_clicked(GtkButton *button, gpointer user_data)
{
    const gchar *label = gtk_button_get_label(button);
    g_print("%s\n", label);
    GtkWindow *win = GTK_WINDOW(user_data);
    gtk_window_destroy(win);
}

static void
activate(GtkApplication *app, gpointer user_data)
{
    DialogOptions *opts = (DialogOptions *)user_data;

    GtkWidget *win = gtk_application_window_new(app);
    gtk_widget_add_css_class(GTK_WIDGET(win), "hypryou-dialog");
    gtk_window_set_title(GTK_WINDOW(win), opts->apptitle ? opts->apptitle : "Dialog");
    gtk_window_set_default_size(GTK_WINDOW(win), 450, 1);
    gtk_window_set_resizable(GTK_WINDOW(win), FALSE);

    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_window_set_child(GTK_WINDOW(win), box);

    if (opts->title)
    {
        GtkWidget *title = gtk_label_new(opts->title);
        gtk_label_set_wrap(GTK_LABEL(title), TRUE);
        gtk_label_set_justify(GTK_LABEL(title), GTK_JUSTIFY_LEFT);
        gtk_label_set_xalign(GTK_LABEL(title), 0);
        gtk_widget_add_css_class(GTK_WIDGET(title), "title");
        gtk_box_append(GTK_BOX(box), title);
        gtk_widget_set_vexpand(GTK_WIDGET(title), true);
        gtk_widget_set_hexpand(GTK_WIDGET(title), true);
    }

    if (opts->text)
    {
        char *text = strip_markup_and_convert_br(opts->text);
        GtkWidget *description = gtk_label_new(text);
        gtk_label_set_wrap(GTK_LABEL(description), TRUE);
        gtk_label_set_justify(GTK_LABEL(description), GTK_JUSTIFY_LEFT);
        gtk_label_set_xalign(GTK_LABEL(description), 0);
        gtk_widget_add_css_class(GTK_WIDGET(description), "description");
        gtk_box_append(GTK_BOX(box), description);
        gtk_widget_set_vexpand(GTK_WIDGET(description), true);
        gtk_widget_set_hexpand(GTK_WIDGET(description), true);
        g_free(text);
    }

    if (opts->buttons_raw)
    {
        GtkWidget *actions_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
        gtk_widget_set_halign(actions_box, GTK_ALIGN_END);
        gtk_box_append(GTK_BOX(box), actions_box);
        gtk_widget_set_vexpand(GTK_WIDGET(actions_box), true);
        gtk_widget_set_hexpand(GTK_WIDGET(actions_box), true);

        gchar **buttons = g_strsplit(opts->buttons_raw, ";", -1);
        for (gchar **b = buttons; *b != NULL; ++b)
        {
            GtkWidget *btn = gtk_button_new_with_label(*b);
            g_signal_connect(btn, "clicked", G_CALLBACK(on_button_clicked), win);
            gtk_widget_set_halign(btn, GTK_ALIGN_END);
            gtk_box_append(GTK_BOX(actions_box), btn);
        }
        g_strfreev(buttons);
    }

    GtkCssProvider *provider = gtk_css_provider_new();
    // Minimum style just in case if gtk4 theme is not set
    gtk_css_provider_load_from_string(provider,
                                      ".title { font-size: 20px; font-weight: 400; }"
                                      ".description { font-size: 16px; font-weight: 300; }"
                                      ".hypryou-dialog { padding: 20px; }");

    gtk_style_context_add_provider_for_display(
        gdk_display_get_default(),
        GTK_STYLE_PROVIDER(provider),
        GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);

    gtk_window_present(GTK_WINDOW(win));
}

int main(int argc, char **argv)
{
    GError *error = NULL;
    GOptionContext *context;

    DialogOptions opts = {0};

    GOptionEntry entries[] = {
        {"title", 't', 0, G_OPTION_ARG_STRING, &opts.title, "Dialog title", "TITLE"},
        {"apptitle", 'p', 0, G_OPTION_ARG_STRING, &opts.apptitle, "App title", "APPTITLE"},
        {"text", 'x', 0, G_OPTION_ARG_STRING, &opts.text, "Dialog text", "TEXT"},
        {"buttons", 'b', 0, G_OPTION_ARG_STRING, &opts.buttons_raw, "Dialog buttons", "BUTTONS"},
        {NULL}};

    context = g_option_context_new(NULL);
    g_option_context_add_main_entries(context, entries, NULL);

    if (!g_option_context_parse(context, &argc, &argv, &error))
    {
        g_printerr("Failed to parse options: %s\n", error->message);
        g_clear_error(&error);
        g_option_context_free(context);
        return 1;
    }
    g_option_context_free(context);

    GtkApplication *app = gtk_application_new("com.koeqaife.hyprland-dialog", G_APPLICATION_DEFAULT_FLAGS);

    g_signal_connect(app, "activate", G_CALLBACK(activate), &opts);

    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);

    return status;
}
