var allIcons = [];
var allEntries = [];
var scrollSpy;

var curProgress = 0;
var curProgressTimer;

var curGaugeProgress = 0;
var curGaugeTimer;

var toastTimer;

function doTabChange(id) {
    var el = $('#'+id);
    el.siblings().removeClass('active');
    var tabsId = id.substring(0, id.indexOf('-'));
    $('body #'+tabsId+'-content > .tab-pane').removeClass('active');
    el.addClass('active');
    $('body #'+id+'-content').addClass('active');
}
function checkTheme() {
    var theme = getStorageData('cui-theme');
    if (theme) {
        $('#themeSwitcher .dropdown__menu a').removeClass('selected');
        if (theme === 'Dark') {
            $('#theme-dark').addClass('selected');
        } else {
            $('#theme-default').addClass('selected');
        }
        switchTheme(theme);
    }
}
function showToast(msg) {
    if (toastTimer) { clearTimeout(toastTimer); }

    $('#styleguidestatus .toast__message').append(msg);
    $('#styleguidestatus').addClass('show');

    toastTimer = setTimeout(function () {
        $('#styleguidestatus').removeClass('show');
        $('#styleguidestatus .toast__message').empty();
        toastTimer = null;
    }, 3000);
}
function switchTheme(theme) {
    if (theme === 'Dark') {
        $('body').attr('data-theme', 'dark');
        $('#theme-code').attr('href', 'public/js/highlight/styles/atom-one-dark.css');
    } else {
        $('body').attr('data-theme', 'default');
        $('#theme-code').attr('href', 'public/js/highlight/styles/atom-one-light.css');
    }
    setStorageData('cui-theme', theme);
}
function copyHexToClipboard(title, hex) {
    clipboard.copy(hex);
    showToast('<div>Copied <b style="color:'+hex+'">'+title+'</b> <span style="color:'+hex+'">'+hex+'</span> to clipboard</div>');
}
function copyIconToClipboard(id) {
    $('#'+id+' a').click(function() {
        clipboard.copy($(this).attr('data-icon'));
        showToast('<div>Copied <b>'+$(this).attr('data-icon')+'</b> to clipboard');
    });
}
function getCssVar(alias) {
    return getComputedStyle(document.body).getPropertyValue(alias);
}
function buildSwatchGroup(id, alias, prefix) {
    var el = $('body #'+id);
    if (el) {
        var colors = getCssVar(alias).split(',');
        colors.forEach(function(color) {
            var hex = getCssVar(prefix+color);
            var html = [
                '<div id="swatch-'+color+'" class="swatch" data-balloon="Click to copy" data-balloon-pos="up" data-balloon-length="medium" onclick="copyHexToClipboard(\''+color+'\',\''+hex+'\')">',
                    '<div class="swatch__color" style="background-color:'+hex+'"></div>',
                    '<div class="swatch__title">'+color+'</div>',
                    '<div class="swatch__hex">'+hex+'</div>',
                '</div>'
            ].join('');
            el.append(html);
        });
    }
}
function populateSwatches() {
    buildSwatchGroup('brand-colors', '--cui-brand-colors', '--cui-color-');
    buildSwatchGroup('theme-colors', '--cui-theme-colors', '--cui-theme-');
    buildSwatchGroup('gray-colors', '--cui-gray-colors', '--cui-color-');
    buildSwatchGroup('status-colors', '--cui-status-colors', '--cui-color-');
    buildSwatchGroup('misc-colors', '--cui-misc-colors', '--cui-color-');
}
function highlightString(str, searchStr) {
    return '<span class="text-bold">' + searchStr + '</span><span>' + str.substring(searchStr.length, str.length) + '</span>';
}
function getStorageData(key) {
    return localStorage.getItem(key);
}
function setStorageData(key, value) {
    localStorage.setItem(key, value);
}
function getQueryParam(key) {
    var url = window.location.search.substring(1);
    var urlVars = url.split('&');
    for (var ii = 0; ii < urlVars.length; ii++) {
        var urlParam = urlVars[ii].split('=');
        if (urlParam[0] === key) {
            return urlParam[1];
        }
    }
}
function setQueryParam(key, value) {
    if (history.pushState) {
        var params = new URLSearchParams(window.location.search);
        params.set(key, value);
        var newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?' + params.toString();
        window.history.pushState({path:newUrl},'',newUrl);
    }
}
function populateSearchEntries() {
    allEntries = [];
    var entries = $('#search-dictionary .searchable');
    for (var ii=0;ii<entries.length;ii++) {
        var retObj = {};
        for (var yy=0;yy<entries[ii].attributes.length;yy++) {
            var attrObj = entries[ii].attributes[yy];
            if (attrObj.name === "data-ref") { retObj.ref = attrObj.value };
            if (attrObj.name === "data-depth") { retObj.depth = attrObj.value };
            if (attrObj.name === "data-category") { retObj.category = attrObj.value };
            if (attrObj.name === "data-name") { retObj.name = attrObj.value };
            if (attrObj.name === "data-description") { retObj.description = attrObj.value };
            if (attrObj.name === "data-group") { retObj.group = attrObj.value };
        }
        var category = retObj.ref.substring(0, retObj.ref.indexOf('-'));
        retObj.ref = 'section-' + category + '.html#' + retObj.ref;
        allEntries.push(retObj);
    }
}
function populateSearchIcons() {
    allIcons = $('body .panel-icon').clone();
    setIcons(allIcons);
}
function removeClassWildcard($element, removals) {
    if (removals.indexOf('*') === -1) {
        // Use native jQuery methods if there is no wildcard matching
        $element.removeClass(removals);
        return $element;
    }

    var patt = new RegExp('\\s' +
            removals.replace(/\*/g, '[A-Za-z0-9-_]+').split(' ').join('\\s|\\s') +
            '\\s', 'g');

    $element.each(function (i, it) {
        var cn = ' ' + it.className + ' ';
        while (patt.test(cn)) {
            cn = cn.replace(patt, ' ');
        }
        it.className = $.trim(cn);
    });

    return $element;
}
function addCards(cnt) {
    $('body #grid').empty();
    for (var ii=1;ii<=cnt;ii++) {
        $('body #grid').append('<div class="panel panel--bordered"><h3 class="text-uppercase base-margin-bottom">Panel '+ii+'</h3><div class="flex"><div class="form-group form-group--inline"><div class="form-group__text"><input id="grid-card-cols" type="number" value="1"><label>Columns</label></div></div><div class="form-group form-group--inline"><div class="form-group__text"><input id="grid-card-rows" type="number" value="1"><label>Rows</label></div></div></div></div>');
    }
    wireCards();
}
function wireAccordion() {
    $('body .accordion > li > a').click(function() {
        $(this).parent().toggleClass('active');
    });
}
function wireScrollToTop() {
    $(window).scroll(function () {
       if ($(this).scrollTop() > 100) {
           $('#scroll-to-top').fadeIn(500);
       } else {
           $('#scroll-to-top').fadeOut(500);
       }
   });
   $('#scroll-to-top').click(function () {
       $("html, body").animate({
           scrollTop: 0
       }, 100);
       return false;
   });
}
function wireCards() {
    $('body #grid .panel').click(function() {
        if ($(this).parent().hasClass('grid--selectable')) {
            $(this).toggleClass('selected');
        }
    });
    $('body #grid-cards').change(function() {
        addCards($(this).val());
    });
    $('body #grid .panel #grid-card-cols').click(function(e) {
        e.stopPropagation();
    });
    $('body #grid .panel #grid-card-cols').change(function() {
        removeClassWildcard($(this).closest('.panel'), 'card--col-*');
        $(this).closest('.panel').addClass('card card--col-'+$(this).val());
    });
    $('body #grid .panel #grid-card-rows').click(function(e) {
        e.stopPropagation();
    });
    $('body #grid .panel #grid-card-rows').change(function() {
        removeClassWildcard($(this).closest('.panel'), 'card--row-*');
        $(this).closest('.panel').addClass('card card--row-'+$(this).val());
    });
}
function calcSearchWindowHeight() {
    var el = $('#search-results');
    var maxHeight = ($(window).height() - $('#search-kit').offset().top - $('#search-kit').height() - 40);
    el.css('max-height', maxHeight + 'px');
}
function shouldHideSidebar() {
    if (window.innerWidth < 768) {
        $('#styleguideSidebar').addClass('sidebar--hidden');
    } else {
        $('#styleguideSidebar').addClass('sidebar--mini');
        $('#styleguideSidebar').removeClass('sidebar--hidden');
    }
}
function startGaugeAnimation() {
    curGaugeTimer = setTimeout(function () {
        curGaugeProgress += Math.floor(Math.random() * 10);
        curGaugeProgress = (curGaugeProgress >= 100) ? 100 : curGaugeProgress;
        $('body #gauge-example').attr('data-percentage', curGaugeProgress);
        $('body #gauge-example #gauge-example-value').html(curGaugeProgress);
        if (curGaugeProgress !== 100) {
            startGaugeAnimation();
        }
    }, 100);
}
function startProgressAnimation() {
    curProgressTimer = setTimeout(function () {
        curProgress += Math.floor(Math.random() * 10);
        curProgress = (curProgress >= 100) ? 100 : curProgress;
        $('body #progressbar-size .progressbar').attr('data-percentage', curProgress);
        $('body #progressbar-size .progressbar .progressbar__label').html(curProgress + '%');
        if (curProgress !== 100) {
            startProgressAnimation();
        }
    }, 100);
}
function jumpTo(ref) {
    document.location.href = "section-"+ref+".html#"+ref;
}
function doNav(url) {
    shouldHideSidebar();
    document.location.href = url;
}
function updateUrl(ref, pattern) {
    var path = window.location.pathname;
    var url = path + '#' + ref;
    history.pushState({ id: url }, 'Cisco UI Kit - ' + ref, url);

    startPageAnimation(pattern);
}
function updateScrollSpy(activeElem) {

    if (scrollSpy) { scrollSpy.destroy(); }
    $('#subTabs').empty();

    for (var ii=0;ii<allEntries.length;ii++) {
        var entry = allEntries[ii];
        if (entry.depth == '2' && entry.name.toLowerCase() == activeElem.toLowerCase()) { // The header
            var anchor = entry.ref.substring(entry.ref.lastIndexOf('#'));
            $('#subTabs').append('<li><a class="scrollLink" href="' + anchor + '" tabindex="0">' + entry.name + '</a>');
        }
        if (entry.depth == '3' && entry.group.toLowerCase() == activeElem.toLowerCase()) { // The data
            var anchor = entry.ref.substring(entry.ref.lastIndexOf('#'));
            $('#subTabs').append('<li><a class="scrollLink" href="' + anchor + '" tabindex="0">' + entry.name + '</a>');
        }
    }
    setTimeout(function() {
        scrollSpy = new Gumshoe('#subTabs a', { offset: 150 });
    }, 250);

    $('#subTabs a.scrollLink').click(function(e) {
        var el = $($(this).attr('href'));
        $('html,body').animate({
            scrollTop: el.offset().top - 120
        }, 250);
    });
}
function updateMainNav(selection) {
    $('#styleguideTabs > li.tab').removeClass('active');
    $('#styleguideTabs-content > .tab-pane').removeClass('active');
    $('#styleguideTabs #styleguideTabs-'+selection).addClass('active');
    $('#styleguideTabs-content #styleguideTabs-'+selection+'-content').addClass('active');
}
function updateMobileNav(selection) {
    $('#styleguideDropdown > .dropdown__menu > a').removeClass('selected');
    $('#styleguideDropdown #styleguideDropdown-'+selection).addClass('selected');
    $('#styleguideDropdown input').val(selection);
}

function wireHomeNav() {
    $('#mobilehome').on('click', function(e) {
        e.stopPropagation();
        var el = $(this).find('input');
        if (!el.hasClass('disabled') && !el.attr('disabled') && !el.hasClass('readonly') && !el.attr('readonly')) {
            $(this).toggleClass('active');
        }
    });
    $('#mobilehome > .dropdown__menu > a').on('click', function(e) {
        var target = e.target.id;
        var selection = target.substring(target.lastIndexOf('-')+1);
        updateHomePageNav(selection);
        updateHomePageNavMobile(selection);
    });
}
function updateHomePageNav(selection) {
    $('#tabshome > li.tab').removeClass('active');
    $('#tabshome-content > .tab-pane').removeClass('active');
    $('#tabshome-'+selection).addClass('active');
    $('#tabshome-'+selection+'-content').addClass('active');
}
function updateHomePageNavMobile(selection) {
    $('#mobilehome > .dropdown__menu > a').removeClass('selected');
    $('#mobilehome #mobilehome-'+selection).addClass('selected');
    $('#mobilehome input').val($('#mobilehome #mobilehome-'+selection).text());
}
function checkUrlAndSetupPage(url) {
    if ((url.indexOf('index.html') !== -1) || (window.location.pathname === '\/')) { // Home page
        if (url.lastIndexOf('#') != -1) { // Check for any home page anchors
            var anchor = url.substring(url.lastIndexOf('#') + 1);
            updateHomePageNav(anchor);
            updateHomePageNavMobile(anchor);
        } else {
            updateHomePageNav('home');
            updateHomePageNavMobile('home');
        }
    }
    else if (url.lastIndexOf('#') != -1) { // Pattern page
        var anchor = url.substring(url.lastIndexOf('#') + 1);
        var str = _.split(anchor, '-')[1];
        var str = str.toLowerCase().replace(/\b[a-z]/g, function(letter) {
            return letter.toUpperCase();
        });

        updateMainNav(str);
        updateMobileNav(str);

        $('#styleguideDropdown > .dropdown__menu > a').on('click', function(e) {
            updateMainNav(e.target.text);
            updateScrollSpy(e.target.text);
            $('html,body').animate({
                scrollTop: 0
            }, 250);
        });

        $('#styleguideTabs > li > a').on('click', function(e) {
            updateMobileNav(e.target.innerText);
            updateScrollSpy(e.target.innerText);
            $('html,body').animate({
                scrollTop: 0
            }, 250);
        });

        setTimeout(function() {
            // Now scroll to the appropriate anchor (if specified in the url)
            var el = document.getElementById(anchor);
            if (el !== null) {
                el.scrollIntoView();
                window.scrollBy(0, -120);
                updateScrollSpy(str);
            }
        }, 100);
    }
}
function startPageAnimation(pattern) {
    if (pattern === 'Gauge') {
        curGaugeProgress = 0;
        startGaugeAnimation();
    } else if (pattern === 'Progressbar') {
        curProgress = 0;
        startProgressAnimation();
    }
}
function doGlobalSearch(searchStr, forceFlag) {
    var results = [];
    searchStr = searchStr.toLowerCase();
    for (var ii=0;ii<allEntries.length;ii++) {
        var entry = allEntries[ii];
        if (_.startsWith(entry.name.toLowerCase(), searchStr) || _.startsWith(entry.group.toLowerCase(), searchStr) || forceFlag) {
            results.push(entry);
        }
    }
    $('#search-results').empty();
    var str = "";
    if (results.length == 0) {
        str = '<a class="text-italic disabled">No results found for query&nbsp;<span class="text-bold">' + searchStr + '</span></a>';
    }
    _.forEach(_.groupBy(results, 'category'), function(value, key) {
        str += '<div class="dropdown__group"><div class="dropdown__group-header">' + key + '</div>';
        _.each(value, function(result) {
            if (result.group !== '') {
                if (result.depth === "2") {
                    str +='<a href="' + result.ref + '"><span class="text-capitalize">' + highlightString(result.group, searchStr) + '</span></a>';
                } else {
                    str += '<a href="' + result.ref + '"><span class="text-capitalize">';
                    str += (_.startsWith(result.group.toLowerCase(), searchStr)) ? highlightString(result.group, searchStr) : result.group;
                    str += '</span>&nbsp;&#8594;&nbsp;<span class="text-capitalize text-italic">';
                    str += (_.startsWith(result.name.toLowerCase(), searchStr)) ? highlightString(result.name, searchStr) : result.name;
                    str += '</span></a>';
                }
            }
        });
        str += '</div>';
    });
    $('#searchKit').addClass('active');
    $('#search-results').append(str);
}
function searchIcons(icon) {
    var ret = [];
    for (var ii=0;ii<allIcons.length;ii++) {
        if (allIcons[ii].innerText.indexOf(icon) !== -1) {
            ret.push(allIcons[ii]);
        }
    }
    return ret;
}
function clearSearch() {
    setIcons(allIcons);
}
function setActiveSlide(slide, animation) {
    $(slide).siblings().removeClass('active');
    $(slide).parent().parent().find('.carousel__slide').removeClass('active slideInLeftSmall slideInRightSmall fadeIn');
    $(slide).addClass('active');
    $(slide).parent().parent().find('#'+slide.id+'-content').addClass('active '+animation);
}
function setIcons (icons) {
    var searchStr = $('#icon-search-input').val();
    if (searchStr !== '') {
        $('#icon-search-results').empty();
        $('#icon-search-results').append(icons);

        // Wire the newly-added icons
        copyIconToClipboard('icon-search-results');

        $('#icon-search-results').removeClass('hide');
        $('#icon-search-container').siblings('.depth-3').addClass('hide');
    } else {
        $('#icon-search-results').addClass('hide');
        $('#icon-search-container').siblings('.depth-3').removeClass('hide');
    }
    $('#icon-count').text(icons.length);
    $('#icon-total-count').text(allIcons.length);
}
function debounce (func, wait) {
    var timeout;
    var context = this, args = arguments;
    clearTimeout(timeout);
    timeout = setTimeout(function () {
        func.apply(context, args);
    }, wait || 0);
}
function openModal (id) {
    $('#'+id).before('<div id="'+id+'-placeholder"></div>').detach().appendTo('body').removeClass('hide');
}
function closeModal (id) {
    $('#'+id).detach().prependTo(('#'+id+'-placeholder')).addClass('hide');
}

$(document).ready(function() {

    // Wire the icon search
    $('#icon-search-input').on('input', function() {
        var searchStr = $('#icon-search-input').val();
        if (searchStr !== '') {
            setIcons(searchIcons(searchStr));
        }
        else {
            clearSearch();
        }
    });

    // Wire the global search
    $('#search-kit').on('click', function() {
        if ($('#search-kit').val() === '') {
            doGlobalSearch('', true);
        }
    });
    $('#search-kit').on('input', function() {
        doGlobalSearch($('#search-kit').val(), false);
    });

    // Wire the gauge reset button
    $('#gauge-start').click(function() {
        if (curGaugeTimer) { clearTimeout(curGaugeTimer); }
        curGaugeProgress = 0;
        startGaugeAnimation();
    });

    // Wire the progressbar reset button
    $('#progressbar-start').click(function() {
        if (curProgressTimer) { clearTimeout(curProgressTimer); }
        curProgress = 0;
        startProgressAnimation();
    });

    // Wire the header sidebar toggle button
    $('#sidebar-toggle').click(function() {
        $('#styleguideSidebar').toggleClass('sidebar--mini');
        $('#sidebar-toggle span:first-child').removeClass();
        if ($('#styleguideSidebar').hasClass('sidebar--mini')) {
            $('#sidebar-toggle span:first-child').addClass('icon-list-menu');
        } else {
            $('#sidebar-toggle span:first-child').addClass('icon-toggle-menu');
        }
    });

    $('#mobile-sidebar-toggle').click(function() {
        $('#styleguideSidebar').removeClass('sidebar--mini');
        $('#styleguideSidebar').toggleClass('sidebar--hidden');
    });

    // Wire the sidebar drawer open/close toggles
    $('#styleguideSidebar .sidebar__drawer > a').click(function(e) {
        e.stopPropagation();
        $(this).parent().siblings().removeClass('sidebar__drawer--opened');
        $(this).parent().toggleClass('sidebar__drawer--opened');
    });

    // Wire the sidebar selected item
    $('#styleguideSidebar .sidebar__item > a').click(function() {
        $('#styleguideSidebar .sidebar__item').removeClass('sidebar__item--selected');
        $(this).parent().addClass('sidebar__item--selected');
    });

    // Wire the sidebar examples
    $('body .sidebar__drawer > a').click(function() {
        $(this).parent().toggleClass('sidebar__drawer--opened');
    });
    $('body .sidebar__item > a').click(function() {
        $(this).parent().siblings().removeClass('sidebar__item--selected');
        $(this).parent().addClass('sidebar__item--selected');
    });

    // Wire the button group examples
    $('body .btn-group .btn').click(function() {
        $(this).siblings().removeClass('selected');
        $(this).addClass('selected');
    });

    // Wire the markup toggles
    $('body .markup').removeClass('active');
    $('body .markup-toggle').click(function() {
        $(this).parent().next().toggleClass('hide');
        $(this).parent().toggleClass('active');

        if ($(this).hasClass('active')) {
            $(this).find('.markup-label').text('Hide code');
        }
        else if (!$(this).hasClass('active')) {
            $(this).find('.markup-label').text('View code');
        }
    });

    // Wire the markup copy to clipboard events
    $('body .clipboard-toggle').click(function() {
        clipboard.copy($(this).parent().parent().find('code.code-raw').text());
        showToast('Copied code to clipboard');
        $(this).addClass('text-bold').text('copied!');
    });

    copyIconToClipboard('icon-main-results');

    // Wire the tabs
    $('body li.tab').click(function() {
        doTabChange(this.id);
        //$(this).siblings().removeClass('active');
        //var tabsId = this.id.substring(0, this.id.indexOf('-'));
        //$('body #'+tabsId+'-content > .tab-pane').removeClass('active');
        //$(this).addClass('active');
        //$('body #'+this.id+'-content').addClass('active');
    });

    // Wire pagination
    $('body ul.pagination > li > a').click(function() {
        var el = $(this).parent().siblings().find('.active');
        $(this).parent().siblings().removeClass('active');
        $(this).parent().addClass('active');
    });

    // Wire closeable alerts
    $('body .alert .alert__close').click(function() {
        $(this).parent().addClass('hide');
    });

    // Wire the Card pattern examples
    $('body a.panel').click(function() {
        $(this).toggleClass('selected');
    });

    // Wire the Advanced Grid example
    $('body #grid-group').click(function() {
        $(this).parent().find('#grid-group').removeClass('selected');
        var cls = 'grid--' + $(this).text();
        $('body .grid').removeClass('grid--3up');
        $('body .grid').removeClass('grid--4up');
        $('body .grid').removeClass('grid--5up');
        $('body .grid').addClass(cls);
        $(this).addClass('selected');
    });

    $('body #grid-cards').change(function() {
        addCards($(this).val());
    });

    $('body #grid-gutters').change(function() {
        $('body #grid').css('gridGap', $(this).val()+'px');
    });

    $('body #grid-selectable').change(function() {
        $('body #grid').toggleClass('grid--selectable');
        $('body .grid .panel').removeClass('selected');
    });

    addCards(15);

    // Wire the carousel examples
    $('body .carousel__controls a.dot').click(function() {
        setActiveSlide(this, 'fadeIn');
    });
    $('body .carousel__controls a.back').click(function() {
        var last = $(this).parent().find('a.dot').last();
        var cur = $(this).parent().find('a.dot.active');
        var active = cur.prev();
        if (active[0].id === "") {
            active = last;
        }
        setActiveSlide(active[0], 'slideInLeftSmall');
    });
    $('body .carousel__controls a.next').click(function() {
        var first = $(this).parent().find('a.dot').first();
        var cur = $(this).parent().find('a.dot.active');
        var active = cur.next();
        if (active[0].id === "") {
            active = first;
        }
        setActiveSlide(active[0], 'slideInRightSmall');
    });

    wireHomeNav();

    // Wire the accordion examples
    wireAccordion();

    // Wire scroll to top button
    wireScrollToTop();

    // Wire the dropdown examples
    $('body .dropdown').not('.ignore').click(function(e) {
        e.stopPropagation();
        var el = $(this).find('input');
        if (!el.hasClass('disabled') && !el.attr('disabled') && !el.hasClass('readonly') && !el.attr('readonly')) {
            $(this).toggleClass('active');
        }
    });
    $('body .dropdown:not(.ignore) .dropdown__menu a').click(function(e) {
        e.stopPropagation();

        var origVal = $(this).parent().parent().find('input').val();
        var newVal = $(this).text();

        $(this).parent().find('a').removeClass('selected');
        $(this).addClass('selected');
        $(this).parent().parent().find('input').val($(this).text());
        $(this).parent().parent().removeClass('active');

        var id = $(this).parent().parent()[0].id;
        if (id === 'themeSwitcher') {
            switchTheme($(this).text());
        }
    });

    // Close dropdowns and open sidebar drawers on clicks outside the dropdowns
    $(document).click(function() {
        $('body .dropdown').not('.ignore').removeClass('active');
        $('#styleguideSidebar .sidebar__drawer').removeClass('sidebar__drawer--opened');
    });

    // Wire the selectable tables
    $('body .table.table--selectable tbody > tr').click(function() {
        $(this).toggleClass('active');
        var cb = $(this).find('td .checkbox input');
        if (cb) {
            cb.prop('checked', !cb.prop('checked'));
        }
    });
    // Wire the table wells example
    $('body #table-wells tbody > tr').click(function() {
        $(this).find('td span.icon-chevron-up').removeClass('icon-chevron-up').addClass('icon-chevron-down');
        $(this).find('td span.icon-chevron-down').removeClass('icon-chevron-down').addClass('icon-chevron-up');
        $(this).next().toggleClass('hide');
    });

    // Wire the global modifiers
    $('body #global-animation').change(function() {
        $('body').toggleClass('cui--animated');
    });
    $('body #global-headermargins').change(function() {
        $('body').toggleClass('cui--headermargins');
    });
    $('body #global-spacing').change(function() {
        $('body').toggleClass('cui--compressed');
    });
    $('body #global-wide').change(function() {
        $('body').toggleClass('cui--wide');
    });
    $('body #global-sticky').change(function() {
        $('body').toggleClass('cui--sticky');
    });

    // Load the changelog
    $.get('changelog.md', function(markdownContent) {
        var converter = new Markdown.Converter();
        $("#changelog-content").html(converter.makeHtml(markdownContent));
    });

    // Load the broadcast file (if it exists)
    $.getJSON('broadcast.json', function(data) {
        if (data && data.text && data.text.length) {
            $("#broadcast-msg").html(data.text);
            $("#broadcast").toggleClass('hide');
        }
    });

    window.addEventListener('hashchange', function (e) {
        checkUrlAndSetupPage(e.newURL);
    }, false);

    // Check for anchor link in the URL
    checkUrlAndSetupPage(window.location.href);

    // Listen of window changes and close the sidebar if necessary
    $(window).resize(function() {
        shouldHideSidebar();
    });

    shouldHideSidebar();
    populateSearchIcons();
    populateSearchEntries();
    populateSwatches();
    checkTheme();
});
