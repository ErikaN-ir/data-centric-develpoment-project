function formatWriting(){
    let unformat = document.querySelector('span.writing1').innerHTML;
    console.log(document.querySelector('span.writing1').innerHTML);
    console.log(unformat);
    let trimmed = unformat.trim();
    let formatted = trimmed.replace(/\n/g, "<br>");
    return document.getElementsByClassName("writing").innerHTML = "Something";
}

$("#writing0").ready(function() {
    let x = 0;
    iterateWriting(x);
});

function iterateWriting(x){
    let w = x++;
    document.getElementsByClass
}