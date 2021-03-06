from .exceptions import CardLinkError, CardValidityError

import re
import string

CARD_WHITE=0
CARD_BLACK=1

CARD_PLACEHOLDER_LENGTH=3

class Card(object):
  def __init__(self, id=-1, text='', type=CARD_WHITE):
    self.id=id
    self.__text=text
    self.type=type
    self.unlinkAll()

  def isValid(self, text=None):
    # implementing some safety
    # if the card is white, no wildcards are allowed
    # also the card may not be empty
    # if the card is black, wildcards are allowed
    # there must even be at least one present
    
    # if text is None, use the current internal text
    if text is None:
      text = self.getInternalText()

    format_iterator = string.Formatter().parse(text)
    placeholders = [p[2] for p in format_iterator if p[2] is not None]
    if self.type==CARD_WHITE and len(placeholders)>0:
      raise CardValidityError({'id':self.id, 'text': 'White cards may not have any placeholders'})
    elif self.type == CARD_WHITE and text.strip(' ')=='':
      raise CardValidityError({'id': self.id, 'text': 'White cards need to contain some text'})
    elif self.type==CARD_BLACK and len(placeholders)==0:
      raise CardValidityError({'id': self.id, 'text': 'Black cards must contain at least one placeholder'})      
    return True

  # sets the internal text (usually just needed internally)
  def setInternalText(self, text):
    # will run through the isValid check
    if self.isValid(text):
      self.__text = text
      self.unlinkAll()

  def getInternalText(self):
    return self.__text

  # retrieves the properly formatted card text
  def getCardText(self):
    return self.formatCardText(self.getInternalText())

  # parses the text and will set it internally too
  def setCardText(self, text):
    format_iterator = string.Formatter().parse(text)
    placeholders = [p[2] for p in format_iterator if p[2] is not None]
    # we don't accept already well formatted placeholders inside the actual card text
    if len(placeholders)>0:
      raise CardValidityError({'id':self.id, 'text': 'invalid text found inside the card text: {%s}'%(placeholders[0])})
    internal_text = self.formatInternalText(text)
    self.setInternalText(internal_text)

  def formatInternalText(self, text):
    return re.sub("( ?)__+([.,?!:;\-/ ])", r"\1{}\2",text)

  def formatCardText(self, text):
    return text.format(*self.__placeholder_texts)
    
  def link(self, card, index = -1):
    if self.type != CARD_BLACK:
      raise CardLinkError("only black cards may link cards")

    if card.type != CARD_WHITE:
      raise CardLinkError("only white cards may be linked to black cards")

    if index == -1:
      try:
        index = self.__links.index(None)
      except ValueError:
        raise CardLinkError("placeholders exceeded")

    try:
      self.__links[index] = card
    except ValueError:
      raise CardLinkError("index out of range")

  def unlink(self, card):

    try:
      self.__links[self.__links.index(card)] = None
    except ValueError:
      raise CardLinkError("card not linked")

  def unlinkAll(self):
    self.__links = [None] * self.placeholders

  @property
  def placeholders(self):
    format_iterator = string.Formatter().parse(self.__text)
    return len([p[2] for p in format_iterator if p[2] is not None])

  @property
  def __placeholder_texts(self):
    texts = []
    for l in self.__links:
      if l is None:
        texts.append('_' * CARD_PLACEHOLDER_LENGTH)
      else:
        texts.append(l.getCardText())

    return texts

  @property
  def links(self):
    return [l for l in self.__links if l is not None]
